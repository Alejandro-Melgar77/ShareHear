import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def create_tray_image():
    """Generates an in-memory 64x64 icon using Pillow."""
    try:
        from PIL import Image, ImageDraw

        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        dc = ImageDraw.Draw(image)
        # Blue circle background
        dc.ellipse((4, 4, 60, 60), fill="#1A73E8")
        # Headphone band
        dc.arc((16, 16, 48, 48), start=180, end=360, fill="white", width=4)
        # Left and right ear cups
        dc.rounded_rectangle((12, 30, 20, 48), radius=3, fill="white")
        dc.rounded_rectangle((44, 30, 52, 48), radius=3, fill="white")
        return image
    except Exception as e:
        logger.debug("Failed to create tray icon with Pillow: %s", e)
        return None


class TrayIcon:
    """System tray icon integration using pystray."""

    def __init__(self, title: str = "BT Bridge Server") -> None:
        self.title = title
        self._icon = None
        self._thread: Optional[threading.Thread] = None

    def start(self, on_show: Callable[[], None], on_quit: Callable[[], None]) -> bool:
        try:
            import pystray

            img = create_tray_image()
            if img is None:
                return False

            menu = pystray.Menu(
                pystray.MenuItem("Mostrar ventana", lambda icon, item: on_show()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Salir", lambda icon, item: on_quit())
            )

            self._icon = pystray.Icon("btbridge", img, self.title, menu)
            self._thread = threading.Thread(target=self._icon.run, daemon=True)
            self._thread.start()
            logger.info("System tray icon started.")
            return True
        except ImportError:
            logger.info("pystray not installed, skipping tray icon.")
            return False
        except Exception as e:
            logger.error("Error starting tray icon: %s", e)
            return False

    def stop(self) -> None:
        if self._icon:
            try:
                self._icon.stop()
            except Exception as e:
                logger.debug("Error stopping tray icon: %s", e)
            self._icon = None
