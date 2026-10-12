package com.btbridge.network

import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.net.DatagramPacket
import java.net.DatagramSocket

class RtpReceiver(
    private val port: Int = 5004,
    private val onPacketReceived: (RtpPacket) -> Unit
) {
    private var socket: DatagramSocket? = null
    private var job: Job? = null
    private var isRunning = false

    fun start(scope: CoroutineScope) {
        if (isRunning) return
        isRunning = true

        job = scope.launch(Dispatchers.IO) {
            try {
                socket = DatagramSocket(port).apply {
                    receiveBufferSize = 1024 * 1024 // 1 MB buffer to avoid drops
                    soTimeout = 1000
                }
                Log.i(TAG, "RtpReceiver bound to UDP port $port")

                val buffer = ByteArray(8192)
                val packet = DatagramPacket(buffer, buffer.size)

                while (isActive && isRunning) {
                    try {
                        socket?.receive(packet)
                        val rtp = RtpPacket.fromBytes(packet.data, packet.length)
                        if (rtp != null) {
                            onPacketReceived(rtp)
                        }
                    } catch (e: java.net.SocketTimeoutException) {
                        // Normal timeout to allow loop check
                    } catch (e: Exception) {
                        if (isRunning) {
                            Log.w(TAG, "UDP receive error: ${e.message}")
                        }
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to start RtpReceiver: ${e.message}")
            } finally {
                closeSocket()
            }
        }
    }

    fun stop() {
        isRunning = false
        job?.cancel()
        job = null
        closeSocket()
    }

    private fun closeSocket() {
        try {
            socket?.close()
        } catch (e: Exception) {
            Log.d(TAG, "Error closing UDP socket: ${e.message}")
        }
        socket = null
        Log.i(TAG, "RtpReceiver stopped")
    }

    companion object {
        private const val TAG = "RtpReceiver"
    }
}
