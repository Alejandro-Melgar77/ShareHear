import platform
import sys

IS_WINDOWS: bool = sys.platform.startswith("win")
IS_LINUX: bool = sys.platform.startswith("linux")
IS_MACOS: bool = sys.platform == "darwin"


def get_platform_name() -> str:
    """Returns normalized platform name."""
    if IS_WINDOWS:
        return "windows"
    elif IS_LINUX:
        return "linux"
    elif IS_MACOS:
        return "macos"
    return platform.system().lower()
