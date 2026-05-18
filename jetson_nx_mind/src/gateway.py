# ==============================================================================
# Component:  jetson_nx_mind
# Module:     gateway.py
# Version:    1.0.0 (gRPC Integration Baseline)
# Purpose:    Central gRPC server framework running on the Jetson to ingest
#             audio streams and state packets from the pi5_body node.
#
# Change History / Release Notes:
# Date        Version   Author    Description of Changes
# ----------  --------  --------  ----------------------------------------------
# 2026-05-18  1.0.0     Steve     Initial connectivity setup and stream logging.
# ==============================================================================

import sys
import os
from concurrent import futures
import grpc

# Append both the parent directory and the proto directory to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../proto')))

import proto.piper_pb2 as piper_pb2
import proto.piper_pb2_grpc as piper_pb2_grpc

class PiperCommsServicer(piper_pb2_grpc.PiperCommsServiceServicer):
    
    def EstablishVoiceSession(self, request_iterator, context):
        print("[GATEWAY] Bidirectional voice stream request received from Body.")
        for frame in request_iterator:
            if frame.chunk_id % 50 == 0:
                print(f"[GATEWAY] Audio Stream Alive. Ingesting chunk ID: {frame.chunk_id} ({len(frame.audio_bytes)} bytes)")
            yield piper_pb2.AudioFrame(chunk_id=frame.chunk_id)

    def SignalStateChange(self, request, context):
        print(f"[GATEWAY] State signal intercepted: Event={request.event_type}, Payload={request.payload}")
        return piper_pb2.StateResponse(accepted=True, message="Event synchronized by Mind kernel.")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    piper_pb2_grpc.add_PiperCommsServiceServicer_to_server(PiperCommsServicer(), server)
    server.add_insecure_port('[::]:50051')
    print("[GATEWAY] Mind Server online and listening on port 50051...")
    server.start()
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("[GATEWAY] Shutting down Mind server gracefully.")

if __name__ == "__main__":
    serve()
