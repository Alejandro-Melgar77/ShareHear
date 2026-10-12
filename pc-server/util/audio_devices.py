import logging
from typing import Any, Dict, List
from util.platform_compat import IS_WINDOWS

logger = logging.getLogger(__name__)


def list_loopback_devices() -> List[Dict[str, Any]]:
    """
    List available loopback/output devices that can capture system audio.
    Prioritizes PyAudioWPatch on Windows (for WASAPI loopback)
    and falls back to sounddevice.
    """
    devices: List[Dict[str, Any]] = []

    if IS_WINDOWS:
        try:
            import pyaudiowpatch as pyaudio

            p = pyaudio.PyAudio()
            try:
                # Get default WASAPI loopback device
                try:
                    default_loopback = p.get_default_wasapi_loopback()
                    devices.append({
                        "index": None,
                        "name": "✨ [Automático] Modo Auricular (Silencia parlantes al conectar)",
                        "channels": default_loopback["maxInputChannels"],
                        "sample_rate": int(default_loopback["defaultSampleRate"]),
                        "is_default": True
                    })
                except Exception as e:
                    logger.debug("No default WASAPI loopback device found: %s", e)

                # Iterate through all WASAPI loopback devices
                for i in range(p.get_device_count()):
                    dev = p.get_device_info_by_index(i)
                    if dev.get("isLoopbackDevice", False):
                        if not any(d["index"] == dev["index"] for d in devices):
                            raw_name = dev["name"]
                            display_name = raw_name
                            if "sharehear" in raw_name.lower():
                                display_name = f"🔊 ShareHear (Salida Silenciosa) [Loopback]"
                            elif "cable" in raw_name.lower():
                                display_name = f"🔊 Cable Virtual VB-CABLE (Silencioso) [Loopback]"
                            elif "high definition" in raw_name.lower():
                                display_name = f"🔊 Canal Silencioso (Altavoces 2- High Definition) [Loopback]"
                            elif "usb speaker" in raw_name.lower():
                                display_name = f"⚠️ Parlantes USB (Altavoces 7- USB Speaker) [Suena en PC]"

                            devices.append({
                                "index": dev["index"],
                                "name": display_name,
                                "raw_name": raw_name,
                                "channels": dev["maxInputChannels"],
                                "sample_rate": int(dev["defaultSampleRate"]),
                                "is_default": False
                            })
            finally:
                p.terminate()
            if devices:
                return devices
        except ImportError:
            logger.warning("PyAudioWPatch is not installed. Falling back to sounddevice.")
        except Exception as e:
            logger.error("Error querying devices with PyAudioWPatch: %s", e)

    # Fallback to sounddevice (Linux / MacOS or fallback on Windows)
    try:
        import sounddevice as sd

        all_devices = sd.query_devices()
        for idx, dev in enumerate(all_devices):
            # On Linux or fallback, identify output or monitor devices
            name = dev.get("name", "")
            max_in = dev.get("max_input_channels", 0)
            max_out = dev.get("max_output_channels", 0)
            samplerate = int(dev.get("default_samplerate", 48000))

            # Include if it has inputs, or mentions monitor/loopback/stereo mix/cable
            is_candidate = (
                max_in > 0 and any(kw in name.lower() for kw in ["loopback", "monitor", "cable", "mezcla", "mix", "virtual"])
            ) or (max_in > 0 and not IS_WINDOWS)

            if is_candidate:
                devices.append({
                    "index": idx,
                    "name": name,
                    "channels": max(max_in, 2),
                    "sample_rate": samplerate,
                    "is_default": False
                })

        # If still empty on sounddevice, add any device with input channels
        if not devices:
            for idx, dev in enumerate(all_devices):
                if dev.get("max_input_channels", 0) > 0:
                    devices.append({
                        "index": idx,
                        "name": dev.get("name", f"Dispositivo {idx}"),
                        "channels": dev.get("max_input_channels", 2),
                        "sample_rate": int(dev.get("default_samplerate", 48000)),
                        "is_default": False
                    })
    except Exception as e:
        logger.error("Error querying devices with sounddevice: %s", e)

    return devices
