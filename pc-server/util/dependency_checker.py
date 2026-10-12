import logging
from typing import Any, Dict, Tuple
from util.platform_compat import IS_LINUX, IS_WINDOWS

logger = logging.getLogger(__name__)


def check_vbaudio() -> Tuple[bool, str]:
    """
    Check if VB-Audio Virtual Cable is available.
    Needed in Windows if injecting microphone audio back to the PC.
    """
    if IS_LINUX:
        return True, "En Linux se utiliza PulseAudio / PipeWire null-sink de forma nativa."

    try:
        import sounddevice as sd
        devices = sd.query_devices()
        for d in devices:
            name = d.get("name", "").lower()
            if "cable input" in name or "cable output" in name or "vb-audio" in name:
                return True, "VB-Audio Virtual Cable detectado correctamente."
        return False, "VB-Audio Cable no detectado (requerido para micrófono virtual en Windows)."
    except Exception as e:
        return False, f"No se pudo consultar dispositivos de audio: {e}"


def check_vigem() -> Tuple[bool, str]:
    """
    Check if ViGEm Bus and vgamepad are available (Phase 4 Gamepad forwarding).
    """
    if IS_LINUX:
        try:
            import uinput  # type: ignore
            return True, "Módulo uinput de Linux disponible para mandos virtuales."
        except ImportError:
            return False, "python-uinput no instalado (opcional para mandos en Linux)."

    try:
        import vgamepad  # type: ignore
        return True, "ViGEm Bus y vgamepad disponibles para mandos virtuales."
    except ImportError:
        return False, "vgamepad / ViGEm Bus no instalado (opcional, para mandos PS4/PS5)."
    except Exception as e:
        return False, f"ViGEm Bus error: {e}"


def get_all_status() -> Dict[str, Dict[str, Any]]:
    """Return dictionary of dependency check results."""
    vb_ok, vb_msg = check_vbaudio()
    vg_ok, vg_msg = check_vigem()
    return {
        "vbaudio": {"ok": vb_ok, "message": vb_msg},
        "vigem": {"ok": vg_ok, "message": vg_msg}
    }
