import logging
import socket
from typing import Optional
from config.settings import Settings
from server.rtp_packet import RtpPacket

logger = logging.getLogger(__name__)


class RtpSender:
    """
    Sends raw PCM audio (or encoded frames) wrapped in RTP packets
    over UDP to the mobile device with zero queuing delay.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.target_ip: Optional[str] = None
        self.target_port: int = settings.audio_port

        self._socket: Optional[socket.socket] = None
        self._seq_number: int = 0
        self._timestamp: int = 0
        self._is_running: bool = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self, target_ip: str, target_port: Optional[int] = None) -> None:
        """Starts the RTP sender towards the target client IP."""
        if self._is_running:
            self.stop()

        self.target_ip = target_ip
        if target_port:
            self.target_port = target_port

        self._seq_number = 0
        self._timestamp = 0

        # Create UDP socket with low-latency options
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Optimal buffer size
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 256 * 1024)
            # Enable QoS DSCP EF (Expedited Forwarding = 0xB8)
            try:
                self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0xB8)
            except Exception:
                pass
        except Exception as e:
            logger.debug("Could not set socket options: %s", e)

        self._is_running = True
        logger.info("RtpSender started for %s:%d (zero-queue low-latency mode)", self.target_ip, self.target_port)

    def stop(self) -> None:
        """Stops the RTP sender and closes the socket."""
        self._is_running = False

        if self._socket:
            try:
                self._socket.close()
            except Exception as e:
                logger.debug("Error closing UDP socket: %s", e)
            self._socket = None

        logger.info("RtpSender stopped.")

    def send_audio(self, pcm_bytes: bytes) -> None:
        """Sends audio data immediately over UDP to eliminate queuing delay."""
        if not self._is_running or not self._socket or not self.target_ip:
            return

        destination = (self.target_ip, self.target_port)

        packet = RtpPacket(
            payload_type=0,
            seq=self._seq_number,
            timestamp=self._timestamp,
            payload=pcm_bytes
        )

        self._seq_number = (self._seq_number + 1) & 0xFFFF
        samples_count = len(pcm_bytes) // (2 * self.settings.channels)
        self._timestamp = (self._timestamp + samples_count) & 0xFFFFFFFF

        try:
            self._socket.sendto(packet.to_bytes(), destination)
        except Exception as e:
            if self._is_running:
                logger.debug("UDP send error: %s", e)
