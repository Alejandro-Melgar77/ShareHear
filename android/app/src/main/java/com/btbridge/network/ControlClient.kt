package com.btbridge.network

import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.io.PrintWriter
import java.net.InetSocketAddress
import java.net.Socket
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ControlClient @Inject constructor(
    private val scope: CoroutineScope
) {
    private var socket: Socket? = null
    private var writer: PrintWriter? = null
    private var readJob: Job? = null

    private val _isConnected = MutableStateFlow(false)
    val isConnected: StateFlow<Boolean> = _isConnected.asStateFlow()

    private val _serverHello = MutableStateFlow<JSONObject?>(null)
    val serverHello: StateFlow<JSONObject?> = _serverHello.asStateFlow()

    private val _latencyMs = MutableStateFlow(0)
    val latencyMs: StateFlow<Int> = _latencyMs.asStateFlow()

    private val _incomingMessages = MutableSharedFlow<JSONObject>(extraBufferCapacity = 64)
    val incomingMessages: SharedFlow<JSONObject> = _incomingMessages.asSharedFlow()

    suspend fun connect(host: String, port: Int = 9001): Boolean = withContext(Dispatchers.IO) {
        disconnect()

        try {
            Log.i(TAG, "Connecting to control server at $host:$port")
            val newSocket = Socket()
            newSocket.connect(InetSocketAddress(host, port), 5000)
            socket = newSocket
            writer = PrintWriter(OutputStreamWriter(newSocket.getOutputStream(), "UTF-8"), true)
            _isConnected.value = true

            // Start reader loop
            readJob = scope.launch(Dispatchers.IO) {
                val reader = BufferedReader(InputStreamReader(newSocket.getInputStream(), "UTF-8"))
                try {
                    while (isActive && _isConnected.value) {
                        val line = reader.readLine() ?: break
                        if (line.isNotBlank()) {
                            try {
                                val json = JSONObject(line)
                                handleIncomingMessage(json)
                            } catch (e: Exception) {
                                Log.w(TAG, "Failed to parse JSON: $line")
                            }
                        }
                    }
                } catch (e: Exception) {
                    Log.d(TAG, "Reader loop ended: ${e.message}")
                } finally {
                    disconnect()
                }
            }
            true
        } catch (e: Exception) {
            Log.e(TAG, "Connection failed: ${e.message}")
            disconnect()
            false
        }
    }

    suspend fun disconnect() = withContext(Dispatchers.IO) {
        _isConnected.value = false
        _serverHello.value = null
        readJob?.cancel()
        readJob = null

        try {
            writer?.close()
        } catch (e: Exception) {
            Log.d(TAG, "Error closing writer: ${e.message}")
        }
        writer = null

        try {
            socket?.close()
        } catch (e: Exception) {
            Log.d(TAG, "Error closing socket: ${e.message}")
        }
        socket = null
        Log.i(TAG, "Disconnected from control server")
    }

    fun sendStartAudio(mode: String = "a2dp", sampleRate: Int = 48000, channels: Int = 2) {
        val json = JSONObject().apply {
            put("type", "start_audio")
            put("mode", mode)
            put("sample_rate", sampleRate)
            put("channels", channels)
        }
        sendMessage(json)
    }

    fun sendStop() {
        val json = JSONObject().apply {
            put("type", "stop")
        }
        sendMessage(json)
    }

    fun sendPong(ts: Long, latencyMs: Int) {
        val json = JSONObject().apply {
            put("type", "pong")
            put("ts", ts)
            put("latency_ms", latencyMs)
        }
        sendMessage(json)
    }

    private fun sendMessage(json: JSONObject) {
        scope.launch(Dispatchers.IO) {
            try {
                writer?.println(json.toString())
            } catch (e: Exception) {
                Log.e(TAG, "Error sending message: ${e.message}")
            }
        }
    }

    private fun handleIncomingMessage(json: JSONObject) {
        val type = json.optString("type", "")
        when (type) {
            "hello" -> {
                Log.i(TAG, "Server hello received: $json")
                _serverHello.value = json
            }
            "ping" -> {
                val ts = json.optLong("ts", System.currentTimeMillis())
                val serverLatency = json.optInt("latency_ms", 0)
                if (serverLatency > 0) {
                    _latencyMs.value = serverLatency
                }
                sendPong(ts, _latencyMs.value)
            }
            "pong" -> {
                val sentTs = json.optLong("ts", 0)
                if (sentTs > 0) {
                    val rtt = (System.currentTimeMillis() - sentTs).toInt()
                    _latencyMs.value = (rtt / 2).coerceAtLeast(1)
                }
            }
        }
        _incomingMessages.tryEmit(json)
    }

    companion object {
        private const val TAG = "ControlClient"
    }
}
