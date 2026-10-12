package com.btbridge.audio

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioDeviceInfo
import android.media.AudioFormat
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.media.AudioTrack
import android.os.Build
import android.util.Log

class AudioPlayer(private val context: Context) {
    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as? AudioManager
    private var audioTrack: AudioTrack? = null
    private var focusRequest: AudioFocusRequest? = null
    private var isPlaying = false

    fun start(sampleRate: Int = 48000, channels: Int = 2): Boolean {
        if (isPlaying) return true

        // Request AudioFocus so phone stops other media (Spotify, YouTube, etc.)
        val hasFocus = requestAudioFocus()
        if (!hasFocus) {
            Log.w(TAG, "AudioFocus request not granted, proceeding anyway")
        }

        val channelConfig = if (channels == 1) {
            AudioFormat.CHANNEL_OUT_MONO
        } else {
            AudioFormat.CHANNEL_OUT_STEREO
        }

        val minBufferSize = AudioTrack.getMinBufferSize(
            sampleRate,
            channelConfig,
            AudioFormat.ENCODING_PCM_16BIT
        )
        // Ultra-low latency buffer size (smallest hardware allowable)
        val bufferSize = minBufferSize

        try {
            val track = AudioTrack.Builder()
                .setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_GAME) // Routes to low-latency FastMixer
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .setFlags(AudioAttributes.FLAG_LOW_LATENCY)
                        .build()
                )
                .setAudioFormat(
                    AudioFormat.Builder()
                        .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                        .setSampleRate(sampleRate)
                        .setChannelMask(channelConfig)
                        .build()
                )
                .setBufferSizeInBytes(bufferSize)
                .setTransferMode(AudioTrack.MODE_STREAM)
                .setPerformanceMode(AudioTrack.PERFORMANCE_MODE_LOW_LATENCY)
                .build()

            // Explicitly route to connected Bluetooth A2DP / BLE device if available
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                val outputDevices = audioManager?.getDevices(AudioManager.GET_DEVICES_OUTPUTS) ?: emptyArray()
                val btDevice = outputDevices.firstOrNull {
                    it.type == AudioDeviceInfo.TYPE_BLUETOOTH_A2DP ||
                    it.type == AudioDeviceInfo.TYPE_BLE_HEADSET ||
                    it.type == AudioDeviceInfo.TYPE_BLE_SPEAKER
                }
                if (btDevice != null) {
                    track.preferredDevice = btDevice
                    Log.i(TAG, "AudioTrack explicitly routed to Bluetooth output: ${btDevice.productName}")
                }
            }

            track.play()
            audioTrack = track
            isPlaying = true

            // Write 1 tiny 20ms frame of silence to prime Bluetooth A2DP immediately
            val frameBytes = (sampleRate / 50) * channels * 2
            val silence = ByteArray(frameBytes)
            track.write(silence, 0, silence.size, AudioTrack.WRITE_NON_BLOCKING)

            Log.i(TAG, "AudioTrack started in ultra-low latency mode ($sampleRate Hz, $channels ch, buffer $bufferSize bytes)")
            return true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to initialize AudioTrack: ${e.message}")
            releaseAudioFocus()
            return false
        }
    }

    fun write(pcmData: ByteArray): Int {
        if (!isPlaying || audioTrack == null) return 0
        return try {
            audioTrack?.write(pcmData, 0, pcmData.size, AudioTrack.WRITE_NON_BLOCKING) ?: 0
        } catch (e: Exception) {
            Log.e(TAG, "AudioTrack write error: ${e.message}")
            0
        }
    }

    fun setVolume(volume: Float) {
        try {
            audioTrack?.setVolume(volume.coerceIn(0f, 1f))
        } catch (e: Exception) {
            Log.e(TAG, "Error setting AudioTrack volume: ${e.message}")
        }
    }

    fun stop() {
        if (!isPlaying) return
        isPlaying = false

        try {
            audioTrack?.pause()
            audioTrack?.flush()
            audioTrack?.stop()
            audioTrack?.release()
        } catch (e: Exception) {
            Log.d(TAG, "Error stopping AudioTrack: ${e.message}")
        }
        audioTrack = null

        releaseAudioFocus()
        Log.i(TAG, "AudioPlayer stopped")
    }

    private fun requestAudioFocus(): Boolean {
        if (audioManager == null) return false

        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val playbackAttributes = AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_GAME)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build()

            val request = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
                .setAudioAttributes(playbackAttributes)
                .setAcceptsDelayedFocusGain(true)
                .setOnAudioFocusChangeListener { focusChange ->
                    Log.d(TAG, "AudioFocus changed: $focusChange")
                    if (focusChange == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT || focusChange == AudioManager.AUDIOFOCUS_LOSS) {
                        if (isPlaying && audioManager != null) {
                            focusRequest?.let { audioManager.requestAudioFocus(it) }
                        }
                    }
                }
                .build()

            focusRequest = request
            audioManager.requestAudioFocus(request) == AudioManager.AUDIOFOCUS_REQUEST_GRANTED
        } else {
            @Suppress("DEPRECATION")
            audioManager.requestAudioFocus(
                { focusChange -> Log.d(TAG, "AudioFocus changed: $focusChange") },
                AudioManager.STREAM_MUSIC,
                AudioManager.AUDIOFOCUS_GAIN
            ) == AudioManager.AUDIOFOCUS_REQUEST_GRANTED
        }
    }

    private fun releaseAudioFocus() {
        if (audioManager == null) return

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            focusRequest?.let { audioManager.abandonAudioFocusRequest(it) }
            focusRequest = null
        } else {
            @Suppress("DEPRECATION")
            audioManager.abandonAudioFocus(null)
        }
    }

    companion object {
        private const val TAG = "AudioPlayer"
    }
}
