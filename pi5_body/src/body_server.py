# ==============================================================================
# Component:  pi5_body
# Module:     body_server.py
# Version:    1.0.0 (gRPC Integration Baseline)
# Purpose:    Hardware client daemon running on the Pi 5 to establish network
#             streaming up to the jetson_nx_mind core.
#
# Change History / Release Notes:
# Date        Version   Author    Description of Changes
# ----------  --------  --------  ----------------------------------------------
# 2026-05-18  1.0.0     Steve     Initial connectivity setup and loop verification.
# ==============================================================================

import sys
import os
import time
import grpc

# Append both the parent directory and the proto directory to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../proto')))

import proto.piper_pb2 as piper_pb2
import proto.piper_pb2_grpc as piper_pb2_grpc

JETSON_IP = "192.168.1.XX"  # <--- REPLACE WITH YOUR JETSON'S LOCAL IP

def generate_mock_audio():
    """Simulates streaming raw microphone chunks over the wire."""
    for i in range(1, 151):  # Stream 150 mock frames
        fake_pcm_chunk = b'\x00' * 3200  # 3200 empty bytes
        yield piper_pb2.AudioFrame(
            audio_bytes=fake_pcm_chunk,
            sample_rate=16000,
            channels=1,
            chunk_id=i
        )
        time.sleep(0.1)  # 100ms chunks

def run():
    endpoint = f"{JETSON_IP}:50051"
    print(f"[BODY] Opening gRPC transport channel to Mind at {endpoint}...")
    
    with grpc.insecure_channel(endpoint) as channel:
        stub = piper_pb2_grpc.PiperCommsServiceStub(channel)
        
        # Test 1: Fire a Unary State Change Packet (Simulating a Wake Word)
        print("[BODY] Test 1: Sending Wake Word state ping...")
        packet = piper_pb2.StatePacket(
            event_type="WAKE_WORD_TRIGGERED",
            payload="piper",
            timestamp=int(time.time() * 1000)
        )
        response = stub.SignalStateChange(packet)
        print(f"[BODY] Mind response: {response.message}")
        
        # Test 2: Fire a Bidirectional Streaming Session
        print("[BODY] Test 2: Spawning bidirectional audio stream loop...")
        responses = stub.EstablishVoiceSession(generate_mock_audio())
        for resp in responses:
            pass
        print("[BODY] Stream test complete. Channel flushed cleanly.")

if __name__ == "__main__":
    run()
