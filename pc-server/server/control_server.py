import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, Optional
from config.settings import Settings
from util.platform_compat import get_platform_name

logger = logging.getLogger(__name__)


class ControlServer:
    """
    Async TCP server for control messages between PC and Mobile.
    Uses newline-delimited JSON.
    """

    def __init__(
        self,
        settings: Settings,
        on_command_callback: Callable[[str, Dict[str, Any]], None],
        on_client_connected: Callable[[str], None],
        on_client_disconnected: Callable[[], None],
        on_latency_update: Optional[Callable[[int], None]] = None
    ) -> None:
        self.settings = settings
        self.on_command_callback = on_command_callback
        self.on_client_connected = on_client_connected
        self.on_client_disconnected = on_client_disconnected
        self.on_latency_update = on_latency_update

        self._server: Optional[asyncio.Server] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._client_ip: Optional[str] = None
        self._is_running = False
        self._ping_task: Optional[asyncio.Task] = None
        self._last_latency: int = 0

    @property
    def client_ip(self) -> Optional[str]:
        return self._client_ip

    @property
    def is_connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def start(self) -> None:
        """Starts the TCP control server."""
        self._is_running = True
        self._server = await asyncio.start_server(
            self._handle_client,
            "0.0.0.0",
            self.settings.control_port
        )
        logger.info("ControlServer listening on 0.0.0.0:%d", self.settings.control_port)

    async def stop(self) -> None:
        """Stops the control server and active client session."""
        self._is_running = False

        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
            self._ping_task = None

        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception as e:
                logger.debug("Error closing client writer: %s", e)
            self._writer = None

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        logger.info("ControlServer stopped.")

    async def send_to_client(self, message: Dict[str, Any]) -> None:
        """Sends a JSON message line to the connected client."""
        if not self._writer or self._writer.is_closing():
            return

        try:
            line = json.dumps(message) + "\n"
            self._writer.write(line.encode("utf-8"))
            await self._writer.drain()
        except Exception as e:
            logger.error("Error sending message to client: %s", e)

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        client_ip = peer[0] if peer else "unknown"

        # Disconnect previous client if any
        if self._writer and not self._writer.is_closing():
            try:
                self._writer.close()
            except Exception:
                pass

        self._writer = writer
        self._client_ip = client_ip
        logger.info("Client connected from %s", client_ip)
        self.on_client_connected(client_ip)

        # Send greeting / hello
        hello_msg = {
            "type": "hello",
            "version": "1.0",
            "name": self.settings.server_name,
            "os": get_platform_name(),
            "caps": ["audio_a2dp", "audio_sco", "hid_gamepad", "hid_keyboard"]
        }
        await self.send_to_client(hello_msg)

        # Start periodic ping task
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
        self._ping_task = asyncio.create_task(self._ping_loop())

        try:
            while self._is_running:
                line = await reader.readline()
                if not line:
                    break

                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue

                try:
                    data = json.loads(line_str)
                    await self._process_client_message(data)
                except json.JSONDecodeError:
                    logger.warning("Received invalid JSON: %s", line_str)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug("Client handler error: %s", e)
        finally:
            logger.info("Client %s disconnected", client_ip)
            if self._ping_task and not self._ping_task.done():
                self._ping_task.cancel()
            self._writer = None
            self._client_ip = None
            self.on_client_disconnected()

    async def _process_client_message(self, data: Dict[str, Any]) -> None:
        msg_type = data.get("type", "")

        if msg_type == "ping":
            ts = data.get("ts", int(time.time() * 1000))
            await self.send_to_client({"type": "pong", "ts": ts, "latency_ms": 0})
        elif msg_type == "pong":
            sent_ts = data.get("ts", 0)
            if sent_ts > 0:
                now_ts = int(time.time() * 1000)
                rtt = max(1, now_ts - sent_ts)
                latency = rtt // 2
                self._last_latency = latency
                if self.on_latency_update:
                    self.on_latency_update(latency)
        else:
            # Delegate command to BridgeManager
            self.on_command_callback(msg_type, data)

    async def _ping_loop(self) -> None:
        """Periodically pings the client to evaluate latency and keep connection alive."""
        while self._is_running and self.is_connected:
            try:
                await asyncio.sleep(1.0)
                if not self.is_connected:
                    break
                ts = int(time.time() * 1000)
                await self.send_to_client({
                    "type": "ping",
                    "ts": ts,
                    "latency_ms": self._last_latency
                })
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("Error in ping loop: %s", e)
                break
