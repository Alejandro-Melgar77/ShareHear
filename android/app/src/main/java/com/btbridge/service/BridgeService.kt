package com.btbridge.service

import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.content.ContextCompat
import com.btbridge.audio.AudioPlayer
import com.btbridge.audio.JitterBuffer
import com.btbridge.bluetooth.BluetoothController
import com.btbridge.model.BridgeState
import com.btbridge.model.BridgeStatus
import com.btbridge.model.BtDevice
import com.btbridge.model.PcDevice
import com.btbridge.network.ControlClient
import com.btbridge.network.RtpReceiver
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class BridgeService : Service() {

    @Inject lateinit var controlClient: ControlClient
    @Inject lateinit var bluetoothController: BluetoothController

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private var playbackJob: Job? = null
    private var wakeLock: PowerManager.WakeLock? = null

    private lateinit var audioPlayer: AudioPlayer
    private lateinit var jitterBuffer: JitterBuffer
    private var rtpReceiver: RtpReceiver? = null

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "BridgeService onCreate")
        BridgeNotification.createChannel(this)

        audioPlayer = AudioPlayer(this)
        jitterBuffer = JitterBuffer(targetDelayFrames = 2)

        val powerManager = getSystemService(Context.POWER_SERVICE) as? PowerManager
        wakeLock = powerManager?.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "BTBridge::PlaybackWakeLock"
        )?.apply {
            setReferenceCounted(false)
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action ?: return START_NOT_STICKY

        when (action) {
            ACTION_START -> {
                val host = intent.getStringExtra(EXTRA_PC_HOST) ?: return START_NOT_STICKY
                val port = intent.getIntExtra(EXTRA_PC_PORT, 9001)
                val audioPort = intent.getIntExtra(EXTRA_PC_AUDIO_PORT, 5004)
                val pcName = intent.getStringExtra(EXTRA_PC_NAME) ?: host
                val btName = intent.getStringExtra(EXTRA_BT_NAME) ?: "Bluetooth"
                val mode = intent.getStringExtra(EXTRA_MODE) ?: "a2dp"

                startBridgeSession(host, port, audioPort, pcName, btName, mode)
            }
            ACTION_STOP -> {
                stopBridgeSession()
                stopSelf()
            }
        }

        return START_NOT_STICKY
    }

    private fun startBridgeSession(
        host: String,
        port: Int,
        audioPort: Int,
        pcName: String,
        btName: String,
        mode: String
    ) {
        val notif = BridgeNotification.buildNotification(
            this,
            BridgeState.CONNECTING,
            deviceName = btName,
            pcName = pcName
        )
        startForeground(BridgeNotification.NOTIFICATION_ID, notif)
        wakeLock?.acquire(4 * 60 * 60 * 1000L) // up to 4 hours

        _serviceStatus.value = BridgeStatus(
            state = BridgeState.CONNECTING,
            pcDevice = PcDevice(pcName, host, port, audioPort),
            btDevice = BtDevice("", btName, isConnected = true)
        )

        serviceScope.launch {
            val connected = controlClient.connect(host, port)
            if (!connected) {
                _serviceStatus.value = _serviceStatus.value.copy(
                    state = BridgeState.ERROR,
                    errorMessage = "No se pudo conectar a la PC ($host:$port)"
                )
                stopBridgeSession()
                return@launch
            }

            _serviceStatus.value = _serviceStatus.value.copy(state = BridgeState.CONNECTED)

            // Start Audio playback in ultra-low latency mode
            audioPlayer.start(sampleRate = 48000, channels = 2)

            // Direct UDP receiver to AudioPlayer (zero-queue, minimal latency)
            rtpReceiver = RtpReceiver(port = audioPort) { packet ->
                audioPlayer.write(packet.payload)
            }
            rtpReceiver?.start(serviceScope)

            // Command PC server to begin audio streaming
            controlClient.sendStartAudio(mode = mode, sampleRate = 48000, channels = 2)

            _serviceStatus.value = _serviceStatus.value.copy(state = BridgeState.STREAMING)

            // Update ongoing notification
            val streamingNotif = BridgeNotification.buildNotification(
                this@BridgeService,
                BridgeState.STREAMING,
                deviceName = btName,
                pcName = pcName,
                latencyMs = controlClient.latencyMs.value
            )
            startForeground(BridgeNotification.NOTIFICATION_ID, streamingNotif)

            // Continuously collect latency updates from pings and reflect in UI
            serviceScope.launch {
                controlClient.latencyMs.collect { lat ->
                    if (lat > 0) {
                        _serviceStatus.value = _serviceStatus.value.copy(latencyMs = lat)
                    }
                }
            }

            // Sync volume from PC if sent
            serviceScope.launch {
                controlClient.incomingMessages.collect { json ->
                    if (json.optString("type") == "volume") {
                        val level = json.optDouble("level", 1.0).toFloat()
                        audioPlayer.setVolume(level)
                    }
                }
            }
        }
    }

    private fun stopBridgeSession() {
        controlClient.sendStop()
        playbackJob?.cancel()
        playbackJob = null

        rtpReceiver?.stop()
        rtpReceiver = null

        audioPlayer.stop()
        jitterBuffer.clear()

        serviceScope.launch {
            controlClient.disconnect()
        }

        try {
            if (wakeLock?.isHeld == true) {
                wakeLock?.release()
            }
        } catch (e: Exception) {
            Log.d(TAG, "Error releasing wake lock: ${e.message}")
        }

        _serviceStatus.value = BridgeStatus(state = BridgeState.IDLE)
        stopForeground(STOP_FOREGROUND_REMOVE)
    }

    override fun onDestroy() {
        super.onDestroy()
        stopBridgeSession()
        serviceScope.cancel()
        Log.i(TAG, "BridgeService onDestroy")
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        private const val TAG = "BridgeService"

        const val ACTION_START = "com.btbridge.action.START"
        const val ACTION_STOP = "com.btbridge.action.STOP"

        const val EXTRA_PC_HOST = "extra_pc_host"
        const val EXTRA_PC_PORT = "extra_pc_port"
        const val EXTRA_PC_AUDIO_PORT = "extra_pc_audio_port"
        const val EXTRA_PC_NAME = "extra_pc_name"
        const val EXTRA_BT_NAME = "extra_bt_name"
        const val EXTRA_MODE = "extra_mode"

        private val _serviceStatus = MutableStateFlow(BridgeStatus())
        val serviceStatus: StateFlow<BridgeStatus> = _serviceStatus.asStateFlow()

        fun startBridge(
            context: Context,
            pcDevice: PcDevice,
            btDevice: BtDevice?,
            mode: String = "a2dp"
        ) {
            val intent = Intent(context, BridgeService::class.java).apply {
                action = ACTION_START
                putExtra(EXTRA_PC_HOST, pcDevice.host)
                putExtra(EXTRA_PC_PORT, pcDevice.port)
                putExtra(EXTRA_PC_AUDIO_PORT, pcDevice.audioPort)
                putExtra(EXTRA_PC_NAME, pcDevice.name)
                putExtra(EXTRA_BT_NAME, btDevice?.name ?: "Auriculares BT")
                putExtra(EXTRA_MODE, mode)
            }
            ContextCompat.startForegroundService(context, intent)
        }

        fun stopBridge(context: Context) {
            val intent = Intent(context, BridgeService::class.java).apply {
                action = ACTION_STOP
            }
            context.startService(intent)
        }
    }
}
