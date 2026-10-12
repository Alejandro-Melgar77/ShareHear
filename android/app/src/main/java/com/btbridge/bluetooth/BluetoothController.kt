package com.btbridge.bluetooth

import android.annotation.SuppressLint
import android.content.Context
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.os.Build
import android.util.Log
import com.btbridge.model.BtDevice
import com.btbridge.model.BtProfileType
import com.btbridge.util.SdkVersionHelper
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class BluetoothController @Inject constructor(
    private val a2dpManager: A2dpManager,
    private val scanner: BluetoothScanner,
    @ApplicationContext private val context: Context
) {
    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as? AudioManager

    private val _selectedDevice = MutableStateFlow<BtDevice?>(null)
    val selectedDevice: StateFlow<BtDevice?> = _selectedDevice.asStateFlow()

    fun selectDevice(device: BtDevice) {
        _selectedDevice.value = device
        Log.i(TAG, "Selected device: ${device.name} (${device.address})")
    }

    fun enableScoMode(): Boolean {
        if (audioManager == null) return false
        Log.i(TAG, "Activating Bluetooth SCO (microphone mode)...")

        return try {
            if (SdkVersionHelper.hasModernSco && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val commDevices = audioManager.availableCommunicationDevices
                val btDevice = commDevices.firstOrNull {
                    it.type == AudioDeviceInfo.TYPE_BLUETOOTH_SCO ||
                    it.type == AudioDeviceInfo.TYPE_BLUETOOTH_A2DP
                }
                if (btDevice != null) {
                    audioManager.setCommunicationDevice(btDevice)
                    true
                } else {
                    Log.w(TAG, "No Bluetooth communication device found")
                    false
                }
            } else {
                @Suppress("DEPRECATION")
                audioManager.startBluetoothSco()
                @Suppress("DEPRECATION")
                audioManager.isBluetoothScoOn = true
                true
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error enabling SCO mode: ${e.message}")
            false
        }
    }

    fun disableScoMode() {
        if (audioManager == null) return
        Log.i(TAG, "Deactivating Bluetooth SCO mode...")

        try {
            if (SdkVersionHelper.hasModernSco && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                audioManager.clearCommunicationDevice()
            } else {
                @Suppress("DEPRECATION")
                audioManager.stopBluetoothSco()
                @Suppress("DEPRECATION")
                audioManager.isBluetoothScoOn = false
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error disabling SCO mode: ${e.message}")
        }
    }

    companion object {
        private const val TAG = "BluetoothController"
    }
}
