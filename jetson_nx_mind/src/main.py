# ==============================================================================
# Component:  jetson_nx_mind
# Module:     main.py
# Version:    1.0.0 (Unified Core Runtime Launcher)
# Purpose:    Provides a single orchestration script to spin up both the 
#             core thread executive loop and the open network gRPC channels.
# ==============================================================================

import time
import sys
from core_exec import ExecutiveKernel
from gateway import start_gateway_server

def main():
    print("=====================================================")
    print("        INITIALIZING PIPER COGNITIVE SUBSTRATE       ")
    print("=====================================================\n")

    # 1. Instantiate the Master Executive Thread Pool Coordinator
    executive = ExecutiveKernel()

    # 2. Start the gRPC Network Communication Channels 
    # (Injects the executive instance to allow bidirectional memory data sharing)
    try:
        grpc_server, servicer = start_gateway_server(executive)
        
        # Pass the active network servicer handle back down into the executive kernel
        executive.gateway = servicer
    except Exception as network_err:
        print(f"[FATAL] Failed to allocate port 50051 interface: {network_err}")
        sys.exit(1)

    # 3. Spin up the visual worker, listening gates, and autonomous tasks
    executive.startup()

    print("\n[SYSTEM] Master execution loop completely active. Press Ctrl+C to stop.")
    
    # Keep main runtime supervisor alive until a terminal intercept event occurs
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SYSTEM] Intercepted shutdown request flag.")
    finally:
        # 4. Graceful Shutdown Sequence execution across all hardware nodes
        executive.shutdown()
        print("[SYSTEM] Stopping network gRPC communication channels...")
        grpc_server.stop(grace=2.0)
        print("[SYSTEM] Core platform execution loop safely terminated.")

if __name__ == "__main__":
    main()
