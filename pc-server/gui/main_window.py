import datetime
import logging
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional
from config.settings import Settings
from gui.tray import TrayIcon
from util.dependency_checker import get_all_status

logger = logging.getLogger(__name__)


class MainWindow(tk.Tk):
    """
    Lightweight, clean Tkinter UI for BT Bridge Server.
    Provides device selection, status monitoring, audio level meter, and system logs.
    """

    def __init__(
        self,
        settings: Settings,
        on_start_callback: Callable[[], None],
        on_stop_callback: Callable[[], None],
        on_device_selected: Callable[[Optional[int]], None],
        on_quit_callback: Callable[[], None]
    ) -> None:
        super().__init__()
        self.settings = settings
        self.on_start_callback = on_start_callback
        self.on_stop_callback = on_stop_callback
        self.on_device_selected = on_device_selected
        self.on_quit_callback = on_quit_callback

        self.title(f"🎧 ShareHear Server — {self.settings.server_name}")
        self.geometry("500x580")
        self.minsize(460, 520)

        # Set window icon
        icon_path = Path(__file__).resolve().parent.parent / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        # Apply dark/clean styling
        self.configure(bg="#1E1E1E")
        self._style = ttk.Style(self)
        try:
            self._style.theme_use("clam")
        except Exception:
            pass

        self._devices_list: List[Dict[str, Any]] = []
        self._is_server_active = False
        self._tray = TrayIcon(f"ShareHear: {self.settings.server_name}")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

    def _build_ui(self) -> None:
        pad_x = 14
        pad_y = 6

        # --- Top Header / Status Frame ---
        header_frame = tk.Frame(self, bg="#252526", padx=pad_x, pady=10)
        header_frame.pack(fill="x")

        self.lbl_status_dot = tk.Label(header_frame, text="●", fg="#E74C3C", bg="#252526", font=("Arial", 16, "bold"))
        self.lbl_status_dot.pack(side="left", padx=(0, 6))

        self.lbl_status_text = tk.Label(
            header_frame,
            text="Servidor detenido",
            fg="#FFFFFF",
            bg="#252526",
            font=("Segoe UI", 12, "bold")
        )
        self.lbl_status_text.pack(side="left")

        # --- Main Action Button ---
        btn_frame = tk.Frame(self, bg="#1E1E1E", padx=pad_x, pady=pad_y)
        btn_frame.pack(fill="x")

        self.btn_toggle_server = tk.Button(
            btn_frame,
            text="▶ INICIAR SERVIDOR",
            bg="#1A73E8",
            fg="white",
            activebackground="#1557B0",
            activeforeground="white",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            pady=8,
            cursor="hand2",
            command=self._on_toggle_click
        )
        self.btn_toggle_server.pack(fill="x")

        # --- Audio Devices Section ---
        dev_frame = tk.LabelFrame(
            self,
            text="Captura de Audio del Sistema",
            bg="#1E1E1E",
            fg="#AAAAAA",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=8
        )
        dev_frame.pack(fill="x", padx=pad_x, pady=pad_y)

        dev_row = tk.Frame(dev_frame, bg="#1E1E1E")
        dev_row.pack(fill="x")

        self.combo_var = tk.StringVar()
        self.combo_devices = ttk.Combobox(
            dev_row,
            textvariable=self.combo_var,
            state="readonly",
            font=("Segoe UI", 9)
        )
        self.combo_devices.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.combo_devices.bind("<<ComboboxSelected>>", self._on_device_changed)

        btn_refresh = tk.Button(
            dev_row,
            text="🔄",
            bg="#333333",
            fg="white",
            relief="flat",
            padx=6,
            command=self.refresh_devices
        )
        btn_refresh.pack(side="right")

        # VB-CABLE status row
        cable_status_frame = tk.Frame(dev_frame, bg="#1E1E1E")
        cable_status_frame.pack(fill="x", pady=(6, 2))

        self._cable_installed = self._check_cable_installed()

        if self._cable_installed:
            cable_status_text = "✅ CABLE Virtual instalado — selecciónalo arriba"
            cable_status_color = "#68D391"
            btn_cable_text = "🔊 Abrir Salida de Sonido de Windows"
            btn_cable_cmd = self._open_windows_sound_settings
            btn_cable_bg = "#2D6A4F"
            btn_cable_fg = "#B7E4C7"
        else:
            cable_status_text = "⚠️ Sin tarjeta virtual — el audio suena en DOS lugares a la vez"
            cable_status_color = "#FC8181"
            btn_cable_text = "🔌 Instalar Tarjeta de Sonido Virtual  ← NECESARIO"
            btn_cable_cmd = self._install_virtual_cable
            btn_cable_bg = "#9B2335"
            btn_cable_fg = "#FED7D7"

        self.lbl_cable_status = tk.Label(
            cable_status_frame,
            text=cable_status_text,
            fg=cable_status_color,
            bg="#1E1E1E",
            font=("Segoe UI", 8, "bold"),
            anchor="w"
        )
        self.lbl_cable_status.pack(fill="x", pady=(0, 4))

        btn_virtual_card = tk.Button(
            dev_frame,
            text=btn_cable_text,
            bg=btn_cable_bg,
            fg=btn_cable_fg,
            activebackground="#1D4044",
            activeforeground="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            pady=5,
            cursor="hand2",
            command=btn_cable_cmd
        )
        btn_virtual_card.pack(fill="x", pady=(0, 2))

        btn_sound_settings = tk.Button(
            dev_frame,
            text="🔊 Abrir Salida de Sonido de Windows",
            bg="#2D3748",
            fg="#63B3ED",
            activebackground="#4A5568",
            activeforeground="white",
            font=("Segoe UI", 8),
            relief="flat",
            pady=3,
            cursor="hand2",
            command=self._open_windows_sound_settings
        )
        btn_sound_settings.pack(fill="x", pady=(0, 2))

        if self._cable_installed:
            tip_text = "💡 En Windows selecciona 'CABLE Input' como salida → solo suenan los auriculares."
        else:
            tip_text = "💡 Instala la tarjeta virtual, luego selecciona 'CABLE Input' como salida de audio."

        self.lbl_sound_tip = tk.Label(
            dev_frame,
            text=tip_text,
            fg="#A0AEC0",
            bg="#1E1E1E",
            font=("Segoe UI", 7),
            justify="left",
            anchor="w"
        )
        self.lbl_sound_tip.pack(fill="x", pady=(2, 0))

        # --- Connection & Diagnostics Section ---
        diag_frame = tk.LabelFrame(
            self,
            text="Estado de Conexión & Red",
            bg="#1E1E1E",
            fg="#AAAAAA",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=8
        )
        diag_frame.pack(fill="x", padx=pad_x, pady=pad_y)

        self.lbl_client = tk.Label(diag_frame, text="Móvil: Esperando conexión...", fg="#DDDDDD", bg="#1E1E1E", anchor="w")
        self.lbl_client.pack(fill="x")

        self.lbl_diag = tk.Label(diag_frame, text="Modo: Inactivo | Latencia RTT: -- ms", fg="#AAAAAA", bg="#1E1E1E", anchor="w")
        self.lbl_diag.pack(fill="x")

        # Audio VU Level Meter
        meter_row = tk.Frame(diag_frame, bg="#1E1E1E")
        meter_row.pack(fill="x", pady=(6, 0))

        tk.Label(meter_row, text="Nivel:", fg="#AAAAAA", bg="#1E1E1E", width=6, anchor="w").pack(side="left")
        self.canvas_level = tk.Canvas(meter_row, height=12, bg="#333333", highlightthickness=0)
        self.canvas_level.pack(side="left", fill="x", expand=True)
        self._level_bar = self.canvas_level.create_rectangle(0, 0, 0, 12, fill="#34A853")

        # --- Dependencies Banner ---
        self.lbl_deps = tk.Label(
            self,
            text="",
            fg="#F1C40F",
            bg="#1E1E1E",
            font=("Segoe UI", 8),
            anchor="w"
        )
        self.lbl_deps.pack(fill="x", padx=pad_x)
        self._update_deps_banner()

        # --- Log Console ---
        log_frame = tk.LabelFrame(
            self,
            text="Registro de Actividad",
            bg="#1E1E1E",
            fg="#AAAAAA",
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=4
        )
        log_frame.pack(fill="both", expand=True, padx=pad_x, pady=pad_y)

        self.txt_log = tk.Text(
            log_frame,
            height=6,
            bg="#121212",
            fg="#CCCCCC",
            font=("Consolas", 8),
            relief="flat",
            wrap="word"
        )
        self.txt_log.pack(fill="both", expand=True)

        # --- Bottom Toolbar ---
        bottom_frame = tk.Frame(self, bg="#1E1E1E", padx=pad_x, pady=pad_y)
        bottom_frame.pack(fill="x")

        btn_tray = tk.Button(
            bottom_frame,
            text="Minimizar a bandeja",
            bg="#2D2D2D",
            fg="#CCCCCC",
            relief="flat",
            font=("Segoe UI", 8),
            command=self.minimize_to_tray
        )
        btn_tray.pack(side="left")

        btn_exit = tk.Button(
            bottom_frame,
            text="Salir",
            bg="#2D2D2D",
            fg="#CCCCCC",
            relief="flat",
            font=("Segoe UI", 8),
            command=self.quit_app
        )
        btn_exit.pack(side="right")

    def _update_deps_banner(self) -> None:
        status = get_all_status()
        notes = []
        if not status["vbaudio"]["ok"]:
            notes.append("⚠️ VB-Audio no detectado (opcional para micro)")
        if not status["vigem"]["ok"]:
            notes.append("⚠️ ViGEm Bus no detectado (opcional para mandos)")
        self.lbl_deps.config(text=" | ".join(notes) if notes else "✓ Todos los componentes recomendados detectados.")

    def _get_base_dir(self) -> str:
        import os
        import sys
        if getattr(sys, 'frozen', False):
            return os.path.dirname(os.path.abspath(sys.executable))
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def set_devices(self, devices: List[Dict[str, Any]]) -> None:
        """Populates the device selector dropdown, prioritizing silent channels."""
        self._devices_list = devices
        names = [d["name"] for d in devices]
        self.combo_devices["values"] = names

        if names:
            sel_idx = 0
            # Prioritize silent channel (High Definition / ShareHear / CABLE)
            for i, d in enumerate(devices):
                dname = d["name"].lower()
                if "silencioso" in dname or "sharehear" in dname or "cable" in dname:
                    sel_idx = i
                    break

            self.combo_devices.current(sel_idx)
            if 0 <= sel_idx < len(devices):
                self.settings.audio_device_index = devices[sel_idx]["index"]
                self.settings.save()

    def refresh_devices(self) -> None:
        from util.audio_devices import list_loopback_devices
        devs = list_loopback_devices()
        self.set_devices(devs)
        self.add_log(f"Lista de dispositivos de audio actualizada ({len(devs)} encontrados)")

    def _check_cable_installed(self) -> bool:
        """Check if VB-CABLE virtual audio device is installed."""
        try:
            import pyaudiowpatch as pyaudio
            p = pyaudio.PyAudio()
            found = False
            for i in range(p.get_device_count()):
                try:
                    info = p.get_device_info_by_index(i)
                    if "cable" in info.get("name", "").lower():
                        found = True
                        break
                except Exception:
                    pass
            p.terminate()
            return found
        except Exception:
            return False

    def _install_virtual_cable(self) -> None:
        import os
        import ctypes
        import tkinter.messagebox as msgbox
        base_dir = self._get_base_dir()
        installer_path = os.path.join(base_dir, "vbcable_driver", "VBCABLE_Setup_x64.exe")
        if os.path.exists(installer_path):
            msg = (
                "Se abrirá el instalador de la Tarjeta de Sonido Virtual.\n\n"
                "Instrucciones:\n"
                "1. Acepta el UAC de Administrador\n"
                "2. Haz clic en 'Install Driver'\n"
                "3. Espera hasta que diga 'Installation successful'\n"
                "4. REINICIA la PC\n\n"
                "Después del reinicio:\n"
                "  → En Windows (barra de tareas), selecciona 'CABLE Input' como salida de audio\n"
                "  → En ShareHear Server, selecciona 'CABLE Output [Loopback]'\n"
                "  → Solo sonarán los auriculares Bluetooth"
            )
            msgbox.showinfo("Instalar Tarjeta de Sonido Virtual", msg)
            ctypes.windll.shell32.ShellExecuteW(None, "runas", installer_path, None, os.path.dirname(installer_path), 1)
            self.add_log("Instalador VB-CABLE iniciado con permisos de Administrador...")
        else:
            bat_path = os.path.join(base_dir, "Instalar-Dispositivo-Virtual-ShareHear.bat")
            if os.path.exists(bat_path):
                ctypes.windll.shell32.ShellExecuteW(None, "runas", bat_path, None, base_dir, 1)
            else:
                self.add_log(f"Instalador no encontrado. Busca: vbcable_driver\\VBCABLE_Setup_x64.exe")

    def _open_windows_sound_settings(self) -> None:
        import ctypes
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "open", "ms-settings:sound", None, None, 1)
            self.add_log("Abriendo configuración de salida de sonido de Windows...")
        except Exception as e:
            self.add_log(f"No se pudo abrir configuración de sonido: {e}")

    def _on_device_changed(self, event=None) -> None:
        idx = self.combo_devices.current()
        if 0 <= idx < len(self._devices_list):
            dev = self._devices_list[idx]
            self.settings.audio_device_index = dev["index"]
            self.settings.save()
            self.add_log(f"Dispositivo seleccionado: {dev['name']}")
            self.on_device_selected(dev["index"])

    def _on_toggle_click(self) -> None:
        if self._is_server_active:
            self.on_stop_callback()
        else:
            self.on_start_callback()

    # --- Thread-Safe Update Methods ---

    def update_status(self, state: str, client_ip: str = "") -> None:
        """Updates connection and status indicators safely."""
        def _apply():
            if state == "STREAMING":
                self._is_server_active = True
                self.lbl_status_dot.config(fg="#2ECC71")
                self.lbl_status_text.config(text="Transmitiendo audio")
                self.btn_toggle_server.config(text="⏹ DETENER TRANSMISIÓN", bg="#E74C3C")
                self.lbl_client.config(text=f"Móvil: Conectado ({client_ip})" if client_ip else "Móvil: Conectado")
            elif state == "CONNECTED":
                self._is_server_active = True
                self.lbl_status_dot.config(fg="#3498DB")
                self.lbl_status_text.config(text="Móvil conectado")
                self.btn_toggle_server.config(text="⏹ DETENER SERVIDOR", bg="#E74C3C")
                self.lbl_client.config(text=f"Móvil: Conectado ({client_ip})")
            elif state == "LISTENING":
                self._is_server_active = True
                self.lbl_status_dot.config(fg="#F39C12")
                self.lbl_status_text.config(text="Esperando conexión del móvil...")
                self.btn_toggle_server.config(text="⏹ DETENER SERVIDOR", bg="#E74C3C")
                self.lbl_client.config(text="Móvil: Esperando conexión...")
            else:
                self._is_server_active = False
                self.lbl_status_dot.config(fg="#E74C3C")
                self.lbl_status_text.config(text="Servidor detenido")
                self.btn_toggle_server.config(text="▶ INICIAR SERVIDOR", bg="#1A73E8")
                self.lbl_client.config(text="Móvil: Inactivo")
                self.lbl_diag.config(text="Modo: Inactivo | Latencia RTT: -- ms")
                self.update_audio_level(-60.0)

        self.after(0, _apply)

    def update_diagnostics(self, mode: str, latency_ms: int) -> None:
        def _apply():
            self.lbl_diag.config(text=f"Modo: {mode} | Latencia RTT: {latency_ms} ms")
        self.after(0, _apply)

    def update_audio_level(self, dbfs: float) -> None:
        """Updates VU level meter (-60 to 0 dBFS)."""
        def _apply():
            try:
                width = self.canvas_level.winfo_width()
                if width <= 1:
                    return
                # Normalize from -60..0 dB to 0..1
                fraction = max(0.0, min(1.0, (dbfs + 60.0) / 60.0))
                bar_width = int(fraction * width)
                # Color based on level: green -> yellow -> red
                color = "#2ECC71"
                if fraction > 0.85:
                    color = "#E74C3C"
                elif fraction > 0.65:
                    color = "#F1C40F"
                self.canvas_level.coords(self._level_bar, 0, 0, bar_width, 12)
                self.canvas_level.itemconfig(self._level_bar, fill=color)
            except Exception:
                pass
        self.after(0, _apply)

    def add_log(self, message: str) -> None:
        """Appends timestamped entry to the log box."""
        def _apply():
            now = datetime.datetime.now().strftime("%H:%M:%S")
            line = f"[{now}] {message}\n"
            self.txt_log.insert("end", line)
            # Limit lines to ~150
            lines = int(self.txt_log.index("end-1c").split(".")[0])
            if lines > 150:
                self.txt_log.delete("1.0", "2.0")
            self.txt_log.see("end")
        self.after(0, _apply)

    def minimize_to_tray(self) -> None:
        """Hides the window and starts the system tray icon."""
        self.withdraw()
        tray_started = self._tray.start(
            on_show=self.restore_from_tray,
            on_quit=self.quit_app
        )
        if not tray_started:
            # If tray couldn't start, restore window
            self.deiconify()

    def restore_from_tray(self) -> None:
        """Restores window from tray."""
        self.after(0, lambda: (self._tray.stop(), self.deiconify()))

    def quit_app(self) -> None:
        """Shuts down server and closes window."""
        self._tray.stop()
        self.on_quit_callback()
        self.destroy()
