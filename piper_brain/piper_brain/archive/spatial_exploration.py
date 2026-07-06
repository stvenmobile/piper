#!/home/steve/piper/venv/bin/python3
# ==============================================================================
# Component: jetson_nx_mind
# Module: spatial_exploration.py
# Version: 1.0.0
# Author: Steve
# ==============================================================================

import time
import sys
import os
import requests
import asyncio
from piper_brain import register_skill

# Add the parent directory to the path so we can import servo_controller
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Assuming ServoController is available in the python path, or in the same directory
# based on the example app.py, it's in the same directory.
# However, for this new project structure, we need to make sure it's accessible.
# If it's not in the same directory, we might need to copy it or adjust the path.
# For now, I'll assume it's available or will be made available.
# If it's from a different package, the import would be different.
# Given the example, I'll use the same import and assume the environment is set up.
# If this fails, I'll need to investigate where servo_controller.py is located in the new structure.
try:
    from servo_controller import ServoController
except ImportError:
    # If not found, try importing from the .hermes location as a fallback for testing
    sys.path.append('/home/steve/.hermes/camera_stream')
    from servo_controller import ServoController

class SpatialExplorer:
    def __init__(self):
        self.servo_controller = ServoController()
        # Raster scan parameters
        self.pan_min = 60
        self.pan_max = 120
        self.tilt_min = 80
        self.tilt_max = 110
        self.step_size = 5
        self.settle_time = 0.3
        
        # Data directory
        self.data_dir = '/home/steve/piper/jetson_nx_mind/data/raw_scan/'
        os.makedirs(self.data_dir, exist_ok=True)

        # Camera stream URLs (from app.py)
        self.cam0_url = 'http://localhost:5000/video_feed/0'
        self.cam1_url = 'http://localhost:5000/video_feed/1'

    async def move_to(self, pan, tilt):
        """
        Moves the servos to the specified pan and tilt angles asynchronously.
        The angles are clamped to the defined raster scan range.
        """
        pan = max(self.pan_min, min(self.pan_max, pan))
        # Inverted logic for tilt: 0 is up, 180 is down.
        # Clamp tilt to the tested safe range.
        tilt = max(self.tilt_min, min(self.tilt_max, tilt))

        await asyncio.to_thread(self.servo_controller.set_pan, pan)
        await asyncio.to_thread(self.servo_controller.set_tilt, tilt)

    async def capture_single_frame_from_stream(self, url):
        """
        Parses an MJPEG stream and extracts exactly one JPEG frame asynchronously.
        """
        try:
            response = await asyncio.to_thread(requests.get, url, stream=True, timeout=5)
            if response.status_code != 200:
                return None
                
            bytes_buffer = b""
            for chunk in response.iter_content(chunk_size=4096):
                bytes_buffer += chunk
                
                # Look for the start and end of a JPEG image
                a = bytes_buffer.find(b'\xff\xd8') # JPEG Start of Image
                b = bytes_buffer.find(b'\xff\xd9') # JPEG End of Image
                
                if a != -1 and b != -1:
                    jpg_bytes = bytes_buffer[a:b+2]
                    return jpg_bytes
        except Exception as e:
            print(f"Stream parsing error: {e}")
        return None

    async def capture_frames(self, pan, tilt):
        """
        Captures a single static frame from both camera MJPEG streams asynchronously.
        """
        left_bytes = await self.capture_single_frame_from_stream(self.cam0_url)
        if left_bytes:
            await asyncio.to_thread(self._write_frame_to_file, os.path.join(self.data_dir, f'frame_p{pan}_t{tilt}_left.jpg'), left_bytes)
        else:
            print(f"[-] Failed to extract frame from Camera 0 at P:{pan} T:{tilt}")

        right_bytes = await self.capture_single_frame_from_stream(self.cam1_url)
        if right_bytes:
            await asyncio.to_thread(self._write_frame_to_file, os.path.join(self.data_dir, f'frame_p{pan}_t{tilt}_right.jpg'), right_bytes)
        else:
            print(f"[-] Failed to extract frame from Camera 1 at P:{pan} T:{tilt}")

    def _write_frame_to_file(self, file_path, data):
        """
        Helper function to write frame data to a file (blocking).
        """
        with open(file_path, 'wb') as f:
            f.write(data)



@register_skill("spatial_exploration")
async def perform_spatial_exploration(area: str = "default"):
    """
    Performs a systematic raster scan of the defined window.
    This is registered as a skill for PiperBrain.
    """
    explorer = SpatialExplorer() # Create an instance for each skill call, or manage as a singleton
    print(f"Starting raster scan for area: {area} from Pan:{explorer.pan_min}-{explorer.pan_max}, Tilt:{explorer.tilt_min}-{explorer.tilt_max}, Step:{explorer.step_size}")

    try:
        await asyncio.to_thread(explorer.servo_controller.center)
        await asyncio.sleep(explorer.settle_time)

        # Raster scan loop
        for tilt in range(explorer.tilt_min, explorer.tilt_max + 1, explorer.step_size):
            # For snake-like pattern, reverse pan direction on alternating rows
            pan_range = range(explorer.pan_min, explorer.pan_max + 1, explorer.step_size)
            if (tilt - explorer.tilt_min) // explorer.step_size % 2 == 1:
                pan_range = reversed(pan_range)
            
            for pan in pan_range:
                await explorer.move_to(pan, tilt)
                print(f"Scanning: Pan={pan}, Tilt={tilt}...")
                await asyncio.sleep(explorer.settle_time)
                await explorer.capture_frames(pan, tilt)

    except asyncio.CancelledError:
        print(f"Skill 'spatial_exploration' for area '{area}' was interrupted. Centering servos...")
        await asyncio.to_thread(explorer.servo_controller.center)
    except Exception as e:
        print(f"Error during spatial exploration: {e}")
    finally:
        await asyncio.to_thread(explorer.servo_controller.center) # Ensure servos are always centered
        print(f"Raster scan for area: {area} complete. Centered servos.")

if __name__ == '__main__':
    async def main():
        explorer = SpatialExplorer()
        await perform_spatial_exploration(area="test_run")

    asyncio.run(main())
