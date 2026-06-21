import sys
import os
import grpc
import cv2
import numpy as np

# Ensure Python can resolve your local compiled protobuf stubs
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import spatial_matrix_pb2
import spatial_matrix_pb2_grpc

def run_receiver():
    target_address = "localhost:50051"
    print(f"[*] Connecting to Spatial Matrix stream at {target_address}...")
    
    with grpc.insecure_channel(target_address) as channel:
        # Match your exact service stub: SpatialMatrix
        stub = spatial_matrix_pb2_grpc.SpatialMatrixStub(channel)
        
        # Match your exact request message: VisionStreamRequest
        request = spatial_matrix_pb2.VisionStreamRequest(
            client_id="fedora_telemetry_node",
            request_compressed=False
        )
        
        try:
            # Match your exact RPC method: StreamVisionMatrix
            stream = stub.StreamVisionMatrix(request)
            print("[+] Connection established! Ingesting Vision Matrix frames...\n")
            
            for frame in stream:
                # 1. Extract image bytes using the correct 'frame_bytes' attribute
                np_arr = np.frombuffer(frame.frame_bytes, dtype=np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
                # 2. Extract Servo and State Telemetry
                pan = frame.current_pan
                tilt = frame.current_tilt
                target_id = frame.active_id if frame.active_id else "None"
                thinking = "[Thinking]" if frame.is_thinking else ""
                
                # 3. Print clean status to console line
                print(f"Pan: {pan:6.1f}° | Tilt: {tilt:6.1f}° | Active ID: {target_id:10} {thinking}", end="\r")
                
                # 4. Render visually
                if img is not None:
                    cv2.putText(img, f"Pan: {pan} Tilt: {tilt} | ID: {target_id}", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.imshow("Piper Matrix Stream", img)
                    
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\n[-] User interrupted window execution.")
                    break
                    
        except grpc.RpcError as e:
            print(f"\n[!] gRPC Stream Error: {e.details()} (Code: {e.code()})")
        except KeyboardInterrupt:
            print("\n[-] Stream stopped manually.")
        finally:
            cv2.destroyAllWindows()

if __name__ == "__main__":
    run_receiver()
