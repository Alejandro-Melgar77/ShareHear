import logging
import math
import struct
import threading
from typing import Any, Callable, Dict, List, Optional
from config.settings import Settings
from util.audio_devices import list_loopback_devices
from util.platform_compat import IS_WINDOWS
from util.volume_controller import WindowsVolumeManager

logger = logging.getLogger(__name__)


class AudioCapture:
    """
    Captures system audio using WASAPI loopback on Windows (PyAudioWPatch)
    or sounddevice on Linux/fallback, applies Windows volume/mute scaling,
    and feeds chunks directly to a callback with ultra-low latency.
    """

    def __init__(
        self,
        settings: Settings,
        on_audio_callback: Callable[[bytes], None],
        on_error_callback: Optional[Callable[[str], None]] = None,
        on_level_callback: Optional[Callable[[float], None]] = None
    ) -> None:
        self.settings = settings
        self.on_audio_callback = on_audio_callback
        self.on_error_callback = on_error_callback
        self.on_level_callback = on_level_callback

        self._is_running = False
        self._pa_instance = None
        self._pa_stream = None
        self._sd_stream = None
        self._capture_thread: Optional[threading.Thread] = None
        self._vol_manager = WindowsVolumeManager()
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._is_running

    def list_devices(self) -> List[Dict[str, Any]]:
        return list_loopback_devices()

    def start(self, device_index: Optional[int] = None) -> bool:
        """Starts capturing system audio in a background thread."""
        with self._lock:
            if self._is_running:
                logger.warning("AudioCapture is already running.")
                return True

            target_idx = device_index if device_index is not None else self.settings.audio_device_index

            if IS_WINDOWS:
                success = self._start_wasapi_loopback(target_idx)
            else:
                success = self._start_sounddevice_capture(target_idx)

            if success:
                self._is_running = True
                logger.info("Audio capture started successfully (device: %s).", target_idx)
            return success

    def stop(self) -> None:
        """Stops the audio capture stream."""
        with self._lock:
            self._is_running = False

            if self._capture_thread and self._capture_thread.is_alive():
                self._capture_thread.join(timeout=0.5)
                self._capture_thread = None

            if self._pa_stream is not None:
                try:
                    self._pa_stream.stop_stream()
                    self._pa_stream.close()
                except Exception as e:
                    logger.debug("Error closing PyAudio stream: %s", e)
                self._pa_stream = None

            if self._pa_instance is not None:
                try:
                    self._pa_instance.terminate()
                except Exception as e:
                    logger.debug("Error terminating PyAudio: %s", e)
                self._pa_instance = None

            if self._sd_stream is not None:
                try:
                    self._sd_stream.stop()
                    self._sd_stream.close()
                except Exception as e:
                    logger.debug("Error closing sounddevice stream: %s", e)
                self._sd_stream = None

            logger.info("Audio capture stopped.")

    def _start_wasapi_loopback(self, device_index: Optional[int]) -> bool:
        try:
            import pyaudiowpatch as pyaudio

            self._pa_instance = pyaudio.PyAudio()

            if device_index is None:
                preferred_device = None
                for i in range(self._pa_instance.get_device_count()):
                    try:
                        d = self._pa_instance.get_device_info_by_index(i)
                        if d.get("isLoopbackDevice", False):
                            dname = d.get("name", "").lower()
                            if "sharehear" in dname:
                                preferred_device = d
                                break
                            elif "cable" in dname and preferred_device is None:
                                preferred_device = d
                            elif "high definition" in dname and preferred_device is None:
                                preferred_device = d
                    except Exception:
                        pass

                if preferred_device is not None:
                    device_info = preferred_device
                else:
                    device_info = self._pa_instance.get_default_wasapi_loopback()
            else:
                try:
                    device_info = self._pa_instance.get_device_info_by_index(device_index)
                except Exception:
                    device_info = self._pa_instance.get_default_wasapi_loopback()

            channels = min(2, device_info.get("maxInputChannels", 2))
            sample_rate = int(device_info.get("defaultSampleRate", self.settings.sample_rate))
            frames_per_buffer = self.settings.chunk_frames

            # Open WASAPI loopback stream for reading
            self._pa_stream = self._pa_instance.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=sample_rate,
                frames_per_buffer=frames_per_buffer,
                input=True,
                input_device_index=device_info["index"]
            )

            self._is_running = True
            self._capture_thread = threading.Thread(
                target=self._wasapi_read_loop,
                args=(frames_per_buffer,),
                daemon=True
            )
            self._capture_thread.start()
            return True

        except Exception as e:
            err_msg = f"Failed to start WASAPI loopback: {e}"
            logger.error(err_msg)
            if self.on_error_callback:
                self.on_error_callback(err_msg)
            logger.info("Falling back to sounddevice capture...")
            return self._start_sounddevice_capture(device_index)

    def _wasapi_read_loop(self, frames_per_buffer: int) -> None:
        """Worker loop that continuously reads from WASAPI loopback stream."""
        vol_mgr = self._vol_manager
        level_cb = self.on_level_callback
        audio_cb = self.on_audio_callback

        while self._is_running and self._pa_stream:
            try:
                data = self._pa_stream.read(frames_per_buffer, exception_on_overflow=False)
                if not data:
                    continue

                # Apply Windows Master Volume and Mute control
                vol, muted = vol_mgr.get_volume_and_mute()
                data = vol_mgr.scale_pcm(data, vol, muted)

                if level_cb:
                    self._calculate_level(data)

                audio_cb(data)
            except Exception as e:
                if self._is_running:
                    logger.debug("Read error in WASAPI capture: %s", e)

    def _start_sounddevice_capture(self, device_index: Optional[int]) -> bool:
        try:
            import numpy as np
            import sounddevice as sd

            def sd_callback(indata, frames, time_info, status):
                if not self._is_running:
                    return

                if indata.dtype == np.float32:
                    scaled = np.clip(indata, -1.0, 1.0) * 32767.0
                    pcm_bytes = scaled.astype(np.int16).tobytes()
                else:
                    pcm_bytes = indata.astype(np.int16).tobytes()

                # Apply Windows volume & mute
                vol, muted = self._vol_manager.get_volume_and_mute()
                pcm_bytes = self._vol_manager.scale_pcm(pcm_bytes, vol, muted)

                if self.on_level_callback:
                    self._calculate_level(pcm_bytes)

                try:
                    self.on_audio_callback(pcm_bytes)
                except Exception as err:
                    logger.error("Error in sounddevice on_audio_callback: %s", err)

            self._sd_stream = sd.InputStream(
                device=device_index,
                channels=self.settings.channels,
                samplerate=self.settings.sample_rate,
                blocksize=self.settings.chunk_frames,
                dtype="int16",
                callback=sd_callback
            )
            self._sd_stream.start()
            return True

        except Exception as e:
            err_msg = f"Failed to start sounddevice capture: {e}"
            logger.error(err_msg)
            if self.on_error_callback:
                self.on_error_callback(err_msg)
            return False

    def _calculate_level(self, pcm_bytes: bytes) -> None:
        """Calculates RMS audio level in dBFS and passes to callback."""
        try:
            count = len(pcm_bytes) // 2
            if count == 0:
                return
            samples = struct.unpack(f"<{count}h", pcm_bytes)
            sum_squares = sum(s * s for s in samples)
            rms = math.sqrt(sum_squares / count)
            if rms > 0:
                db = 20 * math.log10(rms / 32768.0)
            else:
                db = -90.0
            db = max(-60.0, min(0.0, db))
            if self.on_level_callback:
                self.on_level_callback(db)
        except Exception:
            pass
