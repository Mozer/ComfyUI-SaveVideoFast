import sys
from pathlib import Path

# Add current custom node directory to Python path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import node file directly
try:
    from save_video_node import SaveVideoFast
except ImportError:
    # Fallback in case your python file has a different filename
    from .save_video_node import SaveVideoFast

NODE_CLASS_MAPPINGS = {
    "SaveVideoFast": SaveVideoFast
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveVideoFast": "Save Video Fast"
}

# Mount frontend js folder
WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]