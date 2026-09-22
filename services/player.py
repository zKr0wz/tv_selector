import os
import platform
import subprocess
from pathlib import Path


def play_media(file_path):
    path = Path(file_path)

    if not path.exists():
        return {
            "success": False,
            "message": "Media file is not available.",
        }

    system = platform.system()

    try:
        if system == "Windows":
            os.startfile(str(path))

        elif system == "Darwin":
            subprocess.Popen([
                "open",
                str(path),
            ])

        elif system == "Linux":
            subprocess.Popen([
                "xdg-open",
                str(path),
            ])

        else:
            return {
                "success": False,
                "message": (
                    f"Unsupported operating system: "
                    f"{system}"
                ),
            }

    except OSError as error:
        return {
            "success": False,
            "message": str(error),
        }

    return {
        "success": True,
        "message": "Playback started.",
    }