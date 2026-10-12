import logging
import socket
from typing import Optional
from config.settings import Settings
from util.platform_compat import get_platform_name

logger = logging.getLogger(__name__)


class MdnsService:
    """
    Announces the BT Bridge PC server on the local network using mDNS (Bonjour/Avahi),
    allowing Android apps to discover it automatically without typing IP addresses.
    """

    SERVICE_TYPE = "_btbridge._tcp.local."

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._zeroconf = None
        self._service_info = None
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> bool:
        """Registers the mDNS service."""
        try:
            from zeroconf import IPVersion, ServiceInfo, Zeroconf

            local_ip = self._get_local_ip()
            ip_bytes = socket.inet_aton(local_ip)

            safe_name = self.settings.server_name.replace(" ", "-")
            service_name = f"{safe_name}.{self.SERVICE_TYPE}"

            properties = {
                "version": "1.0",
                "os": get_platform_name(),
                "audio_port": str(self.settings.audio_port),
                "control_port": str(self.settings.control_port)
            }

            self._service_info = ServiceInfo(
                type_=self.SERVICE_TYPE,
                name=service_name,
                addresses=[ip_bytes],
                port=self.settings.control_port,
                properties=properties,
                server=f"{safe_name}.local."
            )

            self._zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
            self._zeroconf.register_service(self._service_info)
            self._is_running = True
            logger.info("mDNS service registered: %s (%s:%d)", service_name, local_ip, self.settings.control_port)
            return True

        except ImportError:
            logger.warning("zeroconf library not installed. mDNS discovery disabled.")
            return False
        except Exception as e:
            logger.error("Failed to register mDNS service: %s", e)
            return False

    def stop(self) -> None:
        """Unregisters the mDNS service."""
        if not self._is_running:
            return

        self._is_running = False
        try:
            if self._zeroconf and self._service_info:
                self._zeroconf.unregister_service(self._service_info)
                self._zeroconf.close()
                self._zeroconf = None
                self._service_info = None
            logger.info("mDNS service unregistered.")
        except Exception as e:
            logger.debug("Error stopping zeroconf: %s", e)

    def _get_local_ip(self) -> str:
        """Determines the local IPv4 address connected to the network."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Does not actually establish internet traffic, just queries route table
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip
