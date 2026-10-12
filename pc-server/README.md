# 🖥️ BT Bridge — Servidor PC (Windows & Linux)

Servidor de escritorio ligero que captura el audio del sistema y lo transmite en tiempo real hacia la aplicación móvil Android vía red local (Ethernet/WiFi).

## 🚀 Requisitos Previos

- **Python 3.10+** (Recomendado 3.11 o superior).
- **Windows:** Para captura WASAPI nativa se utiliza `PyAudioWPatch`.
- *(Opcional)* **VB-Audio Virtual Cable:** Requerido si deseas utilizar el modo micrófono bidireccional (Fase 3).
- *(Opcional)* **ViGEm Bus:** Requerido si deseas conectar mandos de PS4/PS5 a través del teléfono (Fase 4).

## 📦 Instalación

1. Abre una terminal (PowerShell o CMD) en este directorio:
   ```powershell
   cd "pc-server"
   ```

2. Instala las dependencias necesarias:
   ```powershell
   pip install -r requirements.txt
   ```

## ▶️ Ejecución

Para iniciar la interfaz gráfica del servidor:
```powershell
python main.py
```

### Características de la Interfaz:
- **Detección automática del nombre del equipo:** Se anuncia en la red con el hostname de Windows/Linux.
- **Descubrimiento automático mDNS (Bonjour):** El teléfono detectará tu PC automáticamente sin tener que ingresar la dirección IP.
- **Selector de dispositivo de audio:** Permite seleccionar la salida de audio específica o el dispositivo predeterminado de Windows.
- **Medidor VU de audio en tiempo real:** Muestra el nivel de señal transmitida.
- **Monitoreo de latencia RTT:** Muestra los milisegundos de retraso en la red.
- **Minimización a la bandeja del sistema:** Puedes ocultar la ventana y dejar el servicio corriendo en segundo plano.
