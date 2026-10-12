import struct


class RtpPacket:
    HEADER_SIZE: int = 12
    DEFAULT_SSRC: int = 0x42544252  # 'BTBR'

    def __init__(
        self,
        payload_type: int,
        seq: int,
        timestamp: int,
        payload: bytes,
        ssrc: int = DEFAULT_SSRC
    ) -> None:
        self.payload_type: int = payload_type & 0x7F
        self.seq: int = seq & 0xFFFF
        self.timestamp: int = timestamp & 0xFFFFFFFF
        self.ssrc: int = ssrc & 0xFFFFFFFF
        self.payload: bytes = payload

    def to_bytes(self) -> bytes:
        """Packs RTP header and payload into bytes."""
        header = struct.pack(
            "!BBHII",
            0x80,               # V=2, P=0, X=0, CC=0
            self.payload_type,  # M=0, PT
            self.seq,
            self.timestamp,
            self.ssrc
        )
        return header + self.payload

    @classmethod
    def from_bytes(cls, data: bytes) -> "RtpPacket":
        """Unpacks RTP packet from bytes."""
        if len(data) < cls.HEADER_SIZE:
            raise ValueError(f"Packet too short: {len(data)} bytes (expected >= {cls.HEADER_SIZE})")

        _, pt, seq, ts, ssrc = struct.unpack_from("!BBHII", data, 0)
        payload = data[cls.HEADER_SIZE:]
        return cls(
            payload_type=pt & 0x7F,
            seq=seq,
            timestamp=ts,
            payload=payload,
            ssrc=ssrc
        )
