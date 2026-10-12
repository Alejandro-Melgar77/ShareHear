# 🎧 ShareHear — Enterprise Audio Bridge

<p align="center">
  <img src="website/assets/logo.svg" alt="ShareHear Logo" width="120" height="120">
</p>

<p align="center">
  <strong>Transforma tu smartphone en un receptor de audio inalámbrico de ultra baja latencia para tu PC</strong>
</p>

<p align="center">
  <a href="https://github.com/Alejandro-Melgar77/ShareHear/releases"><img src="https://img.shields.io/badge/Release-v2.0.0-6366F1?style=for-the-badge&logo=github" alt="Release v2.0"></a>
  <img src="https://img.shields.io/badge/Android-8.0_--_15-06B6D4?style=for-the-badge&logo=android&logoColor=white" alt="Android 8.0-15">
  <img src="https://img.shields.io/badge/Windows-10_%2F_11_x64-818CF8?style=for-the-badge&logo=windows&logoColor=white" alt="Windows 10/11">
  <img src="https://img.shields.io/badge/Cloudflare_Pages-Ready-F38020?style=for-the-badge&logo=cloudflare&logoColor=white" alt="Cloudflare Pages">
  <img src="https://img.shields.io/badge/License-MIT-10B981?style=for-the-badge" alt="License MIT">
</p>

---

## 🌟 ¿Qué es ShareHear?

**ShareHear** es una solución de ingeniería de audio en tiempo real diseñada para eliminar la necesidad de adquirir costosos o inestables adaptadores Bluetooth para computadoras de escritorio.

Mediante un puente de comunicación sobre tu red local Wi-Fi o Ethernet (UDP RTP + TCP JSON), ShareHear captura el audio del sistema operativo Windows y lo transmite directamente a tu teléfono celular, permitiéndote escuchar todo el sonido de tu computadora en cualquier auricular Bluetooth o cableado con sincronización labial perfecta.

---

## 📦 Descargas Directas

| Plataforma | Componente | Formato | Tamaño | Enlace Directo |
| :--- | :--- | :--- | :--- | :--- |
| **PC Windows** | ShareHear Server | `.exe` (Portátil) | ~34.6 MB | [📥 Descargar ShareHear-Server.exe](https://github.com/Alejandro-Melgar77/ShareHear/raw/main/ShareHear-Server.exe) |
| **Android** | ShareHear App | `.apk` (Dual V1+V2) | ~10.3 MB | [📥 Descargar ShareHear.apk](https://github.com/Alejandro-Melgar77/ShareHear/raw/main/ShareHear.apk) |
| **Windows** | Tarjeta de Sonido Virtual | `.bat` | ~1.5 KB | [📥 Descargar Instalador Virtual](https://github.com/Alejandro-Melgar77/ShareHear/raw/main/Instalar-Dispositivo-Virtual-ShareHear.bat) |

---

## 🚀 Arquitectura y Especificaciones Técnicas

- **Frecuencia de Muestreo:** PCM 16-bit Estéreo @ 48,000 Hz (Calidad de estudio sin pérdidas).
- **Transporte de Audio:** UDP en puerto `5004` con cabeceras RTP y búfer adaptativo anti-jitter (~10-20 ms de latencia en Wi-Fi 5 GHz).
- **Canal de Control:** TCP en puerto `9001` con mensajería JSON para handshake y telemetría de latencia Round-Trip Time (RTT).
- **Descubrimiento de Red:** mDNS / DNS-SD nativo (Bonjour) para emparejamiento automático con cero configuración IP.
- **Segundo Plano:** `ForegroundService` persistente en Android y minimización en la bandeja del sistema (`System Tray`) en Windows.
- **Privacidad Absoluta (Zero-Cloud):** Todo el procesamiento y transmisión ocurre estrictamente dentro del perímetro de tu red privada (LAN). Ningún dato ni audio viaja a internet.

---

## 🌐 Despliegue en Cloudflare Pages

El repositorio incluye un frontend estático corporativo de alto rendimiento en la carpeta [`website/`](./website/) optimizado bajo los lineamientos de **UI/UX Pro Max**:

1. En tu panel de **Cloudflare Pages**, selecciona **Create a project &rarr; Connect to Git**.
2. Conecta el repositorio `Alejandro-Melgar77/ShareHear`.
3. Configura los parámetros de compilación:
   - **Framework preset:** `None`
   - **Build command:** *(dejar vacío)*
   - **Build output directory:** `website`
4. Haz clic en **Save and Deploy**. En pocos segundos tu sitio estará en línea en un subdominio `*.pages.dev` o en tu dominio personalizado.

---

## 🛠️ Estructura del Proyecto

```
ShareHear/
├── android/                         # Aplicación nativa Android (Kotlin 2.0 + Jetpack Compose)
│   ├── app/                         # Módulo principal y UI Material Design 3
│   └── build.gradle.kts             # Configuración de compilación Gradle
├── pc-server/                       # Servidor de captura de audio para Windows (Python + WASAPI)
│   ├── gui/                         # Interfaz gráfica de usuario y medidor VU
│   ├── server/                      # Motor de transmisión UDP RTP y servidor TCP
│   └── main.py                      # Punto de entrada del servidor
├── website/                         # Sitio web estático para Cloudflare Pages
│   ├── index.html                   # Landing page accesible con guía de usuario y FAQ
│   ├── styles.css                   # Sistema de diseño UI/UX Pro Max (Inter, Tailwind Tokens)
│   ├── app.js                       # Lógica de tabs, acordeón FAQ y copiado rápido
│   ├── assets/                      # Logotipo y favicon en formato vectorial SVG
│   └── downloads/                   # Descarga directa del APK e instaladores
├── ShareHear-Server.exe             # Binario portable compilado para Windows 10/11 x64
├── ShareHear.apk                    # APK compilado y firmado listo para sideload en Android
├── Iniciar-Pagina-Web.bat           # Lanzador local para probar el sitio web en http://localhost:8080
├── Instalar-Dispositivo-Virtual-ShareHear.bat # Script de instalación de audio virtual silencioso
└── README.md
```

---

## 📄 Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Eres libre de usarlo, modificarlo y compartirlo.
