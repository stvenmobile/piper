# ==============================================================================
# Component:  jetson_nx_mind
# Module:     gateway.py
# Version:    3.4.0 (Unified Orchestration & Intercept Gateway)
# Purpose:    Executes localized neural speech synthesis via Piper ONNX, processes
#             inbound Pi mic arrays via Whisper, and handles distributed memory
#             routing. Intercepts transcription data for biometric enrollment.
#
# Change History / Release Notes:
# Date        Version   Author    Description of Changes
# ----------  --------  --------  ----------------------------------------------
# 2026-05-18  1.0.0     Steve     Initial module architectural definition.
# 2026-05-19  1.4.0     Steve     Shifted playback responsibilities to local Jetson.
# 2026-05-19  2.0.0     Steve     Mapped to chunk.audio_int16_array properties.
# 2026-05-19  3.1.0     Steve     Removed hardcoded localhost model overrides.
# 2026-05-19  3.3.0     Steve     Added ALSA warning suppression handlers.
# 2026-05-19  3.4.0     Steve     Refactored into initialization parameters to
#                                 support Core Executive state sync hooks.
# ==============================================================================

import sys
import os
import ctypes
import threading
from concurrent import futures
import grpc
import numpy as np
from dotenv import load_dotenv

# Load environment tokens from local .env file before firing up hub connections
load_dotenv()

# C-Types intercept routine to drop ALSA stderr warnings into null storage
# This completely eliminates the 'underrun occurred' terminal spam during playback.
ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
def py_error_handler(filename, line, function, err, fmt): pass
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)

def suppress_alsa_errors():
    try:
        asound = ctypes.cdll.LoadLibrary('libasound.so.2')
        asound.snd_lib_error_set_handler(c_error_handler)
    except OSError:
        pass

# Execute suppression before importing sounddevice to catch init warnings
suppress_alsa_errors()
import sounddevice as sd
from piper.voice import PiperVoice
from faster_whisper import WhisperModel

# Import our distributed cognitive orchestration engine
from cognition import CognitiveKernel

# Append both the parent directory and the proto directory to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../proto')))
import proto.piper_pb2 as piper_pb2
import proto.piper_pb2_grpc as piper_pb2_grpc

print("[GATEWAY] Loading high-fidelity Neural Piper engine...")
VOICE_PATH = os.path.expanduser("~/piper/jetson_nx_mind/voices/en_US-hfc_female-medium.onnx")
neural_voice = PiperVoice.load(VOICE_PATH)

print("[GATEWAY] Loading Faster-Whisper cognitive substrate...")
whisper_model = WhisperModel("tiny.en", device="cpu", compute_type="int8")

print("[GATEWAY] Booting local inference cognition core...")
brain = CognitiveKernel()

class PiperCommsServicer(piper_pb2_grpc.PiperCommsServiceServicer):
    def __init__(self, executive_instance=None):
        """Injects a pointer to the master thread orchestrator into the gRPC pipe."""
        self.executive = executive_instance
        self.is_streaming = False
        
        # Intercept Registers for Biometric Enrollment Coordination
        self.latest_transcription = None
        self.transcription_ready = threading.Event()

    def stream_vocalize_text(self, text_payload):
        """Streams text chunks dynamically over the speaker to prevent long-form latency delays."""
        try:
            stream = sd.OutputStream(samplerate=22050, channels=1, dtype='int16')
            stream.start()
            for chunk in neural_voice.synthesize(text_payload):
                stream.write(chunk.audio_int16_array)
            stream.stop()
            stream.close()
        except Exception as e:
            print(f"[GATEWAY] Audio streaming local playback error: {e}")

    def EstablishVoiceSession(self, request_iterator, context):
        print("\n[GATEWAY] Initializing Voice Interaction Thread...")
        self.is_streaming = True
        
        # 1. Handle Proactive Greeting Behavior if not currently conversing
        if self.executive and self.executive.current_state not in ["ENGAGED", "PERCEIVING", "CONVERSING"]:
            print("[GATEWAY] Status: ENGAGED. Executing welcome response...")
            self.stream_vocalize_text("Welcome back, Steve. Neural speech and cognitive sub-systems are fully operational.")
            
        print("[GATEWAY] Capturing remote Pi mic stream...")

        # 2. Collect incoming audio packets streaming over the network from the Pi 5
        audio_buffer = bytearray()
        for frame in request_iterator:
            if len(frame.audio_bytes) > 0:
                audio_buffer.extend(frame.audio_bytes)
            
        print(f"[GATEWAY] Audio buffer finalized ({len(audio_buffer)} bytes). Invoking Whisper decoder...")
        
        transcribed_text = ""
        if len(audio_buffer) > 0:
            try:
                raw_pcm = np.frombuffer(audio_buffer, dtype=np.int16).astype(np.float32) / 32768.0
                segments, info = whisper_model.transcribe(raw_pcm, beam_size=5)
                text_segments = [segment.text for segment in segments]
                transcribed_text = " ".join(text_segments).strip()
                
                print(f"\n[STT RESULT]: \"{transcribed_text}\"")
                
            except Exception as e:
                print(f"[GATEWAY] Error processing audio buffer arrays: {e}")
        else:
            print("[GATEWAY] Error: Processing aborted due to empty inbound buffer.")
            self.is_streaming = False
            yield piper_pb2.AudioFrame(chunk_id=404, audio_bytes=b'')
            return

        # 3. Memory & Registration Routing Hooks
        if transcribed_text:
            # CHECK GATING STATE: Is the Visual Thread currently waiting for an Enrollment Name?
            if self.executive and self.executive.current_state == "PERCEIVING":
                print("[GATEWAY] Intercepted transcription string for enrollment registration.")
                self.latest_transcription = transcribed_text
                self.transcription_ready.set()  # Trip thread gate to unblock the visual tracker
                self.is_streaming = False
                yield piper_pb2.AudioFrame(chunk_id=200, audio_bytes=b'')
                return

            # Pass standard conversational queries straight out to the RTX 5070
            piper_reply = brain.generate_response(transcribed_text)
            
            print(f"\n[LLM REPLY]:\n{piper_reply}\n")
            print("[GATEWAY] Streaming deep-dive reply directly to local USB speaker...")
            
            self.stream_vocalize_text(piper_reply)
        else:
            print("[GATEWAY] No recognizable speech detected. Skipping cognitive inference.")
            self.stream_vocalize_text("I didn't catch that. Could you please repeat your command?")
        
        print("[GATEWAY] Transaction evaluation loop complete. Closing stream state cleanly.")
        self.is_streaming = False
        yield piper_pb2.AudioFrame(chunk_id=999, audio_bytes=b'')

    def SignalStateChange(self, request, context):
        print(f"[GATEWAY] State signal intercepted: Event={request.event_type}, Payload={request.payload}")
        return piper_pb2.StateResponse(accepted=True, message="Event synchronized by Mind kernel.")

def start_gateway_server(executive_instance):
    """Initializes and exposes the gRPC server layer while linking it to the runtime core."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Instantiate the servicer explicitly injecting the master thread controller reference
    servicer = PiperCommsServicer(executive_instance=executive_instance)
    
    piper_pb2_grpc.add_PiperCommsServiceServicer_to_server(servicer, server)
    server.add_insecure_port('[::]:50051')
    server.start()
    return server, servicer
