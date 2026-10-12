import json
import os
import socket
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Settings:
    server_name: str = field(default_factory=socket.gethostname)
    control_port: int = 9001
    audio_port: int = 5004
    mic_port: int = 5005
    hid_port: int = 9002
    sample_rate: int = 48000
    channels: int = 2
    chunk_frames: int = 960  # 20ms at 48kHz
    audio_device_index: Optional[int] = None

    @classmethod
    def get_config_path(cls) -> Path:
        base_dir = Path(__file__).resolve().parent
        return base_dir / "settings.json"

    def save(self) -> None:
        """Persist settings to JSON file."""
        config_path = self.get_config_path()
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=4)
        except Exception as e:
            print(f"Warning: Failed to save settings to {config_path}: {e}")

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from JSON file or return defaults."""
        config_path = cls.get_config_path()
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls(**data)
            except Exception as e:
                print(f"Warning: Failed to load settings from {config_path}: {e}, using defaults")
        return cls()
