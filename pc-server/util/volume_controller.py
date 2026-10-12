import logging
from typing import Optional, Tuple
import numpy as np
from util.platform_compat import IS_WINDOWS

logger = logging.getLogger(__name__)


class WindowsVolumeManager:
    """
    Monitors and reads Windows Master Volume so that volume adjustments
    on the PC are directly applied to the streamed audio and synced to the phone.
    """

    def __init__(self) -> None:
        self._endpoint_volume = None
        self._init_endpoint()

    def _init_endpoint(self) -> None:
        if not IS_WINDOWS:
            return
        try:
            from pycaw.pycaw import AudioUtilities
            speakers = AudioUtilities.GetSpeakers()
            if speakers and hasattr(speakers, "EndpointVolume"):
                self._endpoint_volume = speakers.EndpointVolume
                logger.info("WindowsVolumeManager initialized on: %s", getattr(speakers, "FriendlyName", "Default"))
        except Exception as e:
            logger.debug("Could not initialize WindowsVolumeManager: %s", e)
            self._endpoint_volume = None

    def get_volume_and_mute(self) -> Tuple[float, bool]:
        """Returns (scalar_volume [0.0..1.0], is_muted [bool])."""
        if not self._endpoint_volume:
            # Re-try init
            self._init_endpoint()
            if not self._endpoint_volume:
                return 1.0, False

        try:
            vol = float(self._endpoint_volume.GetMasterVolumeLevelScalar())
            muted = bool(self._endpoint_volume.GetMute())
            return vol, muted
        except Exception:
            self._init_endpoint()
            return 1.0, False

    @staticmethod
    def scale_pcm(pcm_bytes: bytes, volume_scalar: float, is_muted: bool) -> bytes:
        """Scales 16-bit PCM samples by the volume scalar."""
        if is_muted or volume_scalar <= 0.001:
            return b"\x00" * len(pcm_bytes)

        if abs(volume_scalar - 1.0) < 0.01:
            return pcm_bytes

        try:
            arr = np.frombuffer(pcm_bytes, dtype=np.int16)
            scaled = np.clip(arr.astype(np.float32) * volume_scalar, -32768, 32767).astype(np.int16)
            return scaled.tobytes()
        except Exception:
            return pcm_bytes
