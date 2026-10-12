import asyncio
import logging
import sys
import threading
from typing import Any, Dict, Optional
from config.settings import Settings
from gui.main_window import MainWindow
from server.audio_capture import AudioCapture
from server.control_server import ControlServer
from server.mdns_service import MdnsService
from server.rtp_sender import RtpSender
from util.audio_devices import list_loopback_devices
from util.platform_compat import IS_WINDOWS
from util.windows_audio_router import WindowsAudioRouter

# Configure root logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("btbridge-server")


class BridgeManager:
    """
    Coordinates the networking, audio streaming, mDNS discovery,
    and control messaging for BT Bridge Server.
    """

    def __init__(self, settings: Settings, window: MainWindow) -> None:
        self.settings = settings
        self.window = window
        self.audio_router = WindowsAudioRouter() if IS_WINDOWS else None

        self.state: str = "STOPPED"  # STOPPED, LISTENING, CONNECTED, STREAMING
        self.current_client_ip: Optional[str] = None
        self.current_mode: str = "A2DP"
        self.current_latency_ms: int = 0

        # Background asyncio loop
        self.loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._loop_thread.start()

        # Components
        self.mdns = MdnsService(self.settings)
        self.rtp_sender = RtpSender(self.settings)
        self.audio_capture = AudioCapture(
            settings=self.settings,
            on_audio_callback=self._on_audio_captured,
            on_error_callback=self._on_audio_error,
            on_level_callback=self._on_audio_level
        )
        self.control_server = ControlServer(
            settings=self.settings,
            on_command_callback=self._on_client_command,
            on_client_connected=self._on_client_connected,
            on_client_disconnected=self._on_client_disconnected,
            on_latency_update=self._on_latency_update
        )

    def _run_async_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def start_server(self) -> None:
        """Starts mDNS discovery and TCP control server."""
        if self.state != "STOPPED":
            return

        self.window.add_log(f"Iniciando servidor en puerto de control {self.settings.control_port}...")
        self.mdns.start()
        self.window.add_log(f"Servicio mDNS anunciado como '{self.settings.server_name}'")

        future = asyncio.run_coroutine_threadsafe(self.control_server.start(), self.loop)
        try:
            future.result(timeout=3.0)
            self.state = "LISTENING"
            self.window.update_status(self.state)
            self.window.add_log("Servidor activo. Esperando conexión de la app móvil...")
        except Exception as e:
            logger.error("Failed to start control server: %s", e)
            self.window.add_log(f"Error al iniciar servidor: {e}")
            self.stop_server()

    def stop_server(self) -> None:
        """Stops streaming, control server, and mDNS discovery."""
        self.window.add_log("Deteniendo servidor...")
        self.stop_audio_stream()

        future = asyncio.run_coroutine_threadsafe(self.control_server.stop(), self.loop)
        try:
            future.result(timeout=2.0)
        except Exception:
            pass

        self.mdns.stop()
        self.state = "STOPPED"
        self.current_client_ip = None
        self.window.update_status(self.state)
        self.window.add_log("Servidor detenido.")

    def start_audio_stream(self, client_ip: str) -> None:
        """Starts audio capture and UDP RTP sender towards client IP."""
        self.current_client_ip = client_ip
        self.window.add_log(f"Iniciando flujo de audio hacia {client_ip}:{self.settings.audio_port}...")

        # Switch Windows default output to silent/virtual channel (like connecting Bluetooth headset)
        if self.audio_router and self.settings.audio_device_index is None:
            routed_name = self.audio_router.route_to_sharehear()
            if routed_name:
                self.window.add_log(f"Salida de Windows redirigida a '{routed_name}' (parlantes silenciados automáticamente).")

        self.rtp_sender.start(client_ip, self.settings.audio_port)
        capture_ok = self.audio_capture.start(self.settings.audio_device_index)

        if capture_ok:
            self.state = "STREAMING"
            self.window.update_status(self.state, client_ip)
            self.window.add_log("Audio en vivo transmitiéndose.")
        else:
            self.window.add_log("Error al iniciar captura de audio. Revisa el dispositivo seleccionado.")
            self.rtp_sender.stop()
            if self.audio_router:
                self.audio_router.restore_original_device()

    def stop_audio_stream(self) -> None:
        """Stops audio capture and RTP transmission."""
        if self.state == "STREAMING":
            self.audio_capture.stop()
            self.rtp_sender.stop()
            if self.audio_router and self.audio_router.restore_original_device():
                self.window.add_log("Salida de audio de Windows restaurada a los parlantes de la PC.")
            self.state = "CONNECTED" if self.current_client_ip else "LISTENING"
            self.window.update_status(self.state, self.current_client_ip or "")
            self.window.add_log("Transmisión de audio detenida.")

    # --- Callbacks ---

    def _on_audio_captured(self, pcm_bytes: bytes) -> None:
        self.rtp_sender.send_audio(pcm_bytes)

    def _on_audio_error(self, message: str) -> None:
        self.window.add_log(f"Audio Error: {message}")

    def _on_audio_level(self, dbfs: float) -> None:
        self.window.update_audio_level(dbfs)

    def _on_client_connected(self, client_ip: str) -> None:
        self.current_client_ip = client_ip
        self.state = "CONNECTED"
        self.window.update_status(self.state, client_ip)
        self.window.add_log(f"Móvil conectado desde IP {client_ip}")

    def _on_client_disconnected(self) -> None:
        self.window.add_log("Móvil desconectado.")
        self.stop_audio_stream()
        if self.state != "STOPPED":
            self.state = "LISTENING"
            self.window.update_status(self.state)

    def _on_client_command(self, cmd_type: str, data: Dict[str, Any]) -> None:
        self.window.add_log(f"Comando recibido: {cmd_type}")

        if cmd_type == "start_audio":
            self.current_mode = data.get("mode", "a2dp").upper()
            self.window.update_diagnostics(self.current_mode, self.current_latency_ms)
            if self.current_client_ip:
                self.start_audio_stream(self.current_client_ip)
        elif cmd_type == "stop":
            self.stop_audio_stream()

    def _on_latency_update(self, latency_ms: int) -> None:
        self.current_latency_ms = latency_ms
        self.window.update_diagnostics(self.current_mode, latency_ms)

    def shutdown(self) -> None:
        """Clean shutdown of background resources."""
        if self.audio_router:
            self.audio_router.restore_original_device()
        self.stop_server()
        try:
            self.loop.call_soon_threadsafe(self.loop.stop)
            if self._loop_thread.is_alive():
                self._loop_thread.join(timeout=1.0)
        except Exception:
            pass


def main() -> None:
    settings = Settings.load()
    devices = list_loopback_devices()

    window: Optional[MainWindow] = None
    manager: Optional[BridgeManager] = None

    def on_start() -> None:
        if manager:
            manager.start_server()

    def on_stop() -> None:
        if manager:
            manager.stop_server()

    def on_device_selected(dev_idx: Optional[int]) -> None:
        settings.audio_device_index = dev_idx
        settings.save()
        if manager and manager.state == "STREAMING":
            # Restart capture with new device
            manager.audio_capture.stop()
            manager.audio_capture.start(dev_idx)

    def on_quit() -> None:
        if manager:
            manager.shutdown()

    window = MainWindow(
        settings=settings,
        on_start_callback=on_start,
        on_stop_callback=on_stop,
        on_device_selected=on_device_selected,
        on_quit_callback=on_quit
    )

    manager = BridgeManager(settings=settings, window=window)
    window.set_devices(devices)
    window.add_log(f"BT Bridge Server listo en {settings.server_name}")

    try:
        window.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        if manager:
            manager.shutdown()
        sys.exit(0)


if __name__ == "__main__":
    main()
