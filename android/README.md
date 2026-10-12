# 🎧 ShareHear — Aplicación Android (Kotlin + Jetpack Compose)

Aplicación móvil nativa en Kotlin para Android que convierte tu teléfono en un receptor Bluetooth universal para una PC sin hardware nativo.

## ✨ Novedades y Características

- **Nuevo Nombre:** ShareHear
- **Icono e Identidad:** Logo moderno con diseño de auriculares holográficos y ondas sonoras en gradiente neón.
- **Compatibilidad Ampliada:** Soporte desde Android 8.0 (API 26) hasta Android 15 (API 35).
- **Firma Dual V1 + V2:** Garantiza que el instalador de Android (PackageInstaller) pueda instalar el APK directamente por sideload sin errores de verificación.
- **Arquitectura:** Kotlin 2.0, Jetpack Compose, Material Design 3, Dagger Hilt.
- **Descubrimiento de Red:** mDNS / DNS-SD nativo (`android.net.nsd.NsdManager`).
- **Protocolo de Audio:** Paquetes RTP sobre UDP (puerto 5004) con búfer adaptativo (Jitter Buffer).
- **Protocolo de Control:** Conexión TCP (puerto 9001) con mensajería JSON en tiempo real.
- **Gestión de Audio:** `AudioTrack` de baja latencia con adquisición de `AudioFocus` exclusiva.
- **Segundo Plano:** `ForegroundService` persistente (`BridgeService`) con notificación continua en la barra de tareas.

## 📦 Archivo Instalador Listo para Usar

El archivo compilado listo para instalar se encuentra en la raíz del proyecto:
`ShareHear.apk`

---

## 🛠️ Cómo Recompilar manualmente

Si deseas volver a compilar el APK en el futuro, ejecuta desde la carpeta `android`:
```powershell
.\gradlew.bat assembleDebug
```
El APK se generará en:
`app\build\outputs\apk\debug\app-debug.apk`
