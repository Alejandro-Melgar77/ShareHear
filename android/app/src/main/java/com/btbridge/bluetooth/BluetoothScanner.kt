package com.btbridge.bluetooth

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothClass
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.content.Context
import android.util.Log
import com.btbridge.model.BtDevice
import com.btbridge.model.BtProfileType
import com.btbridge.util.PermissionHelper
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class BluetoothScanner @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
    val bluetoothAdapter: BluetoothAdapter? = bluetoothManager?.adapter

    private val _pairedDevices = MutableStateFlow<List<BtDevice>>(emptyList())
    val pairedDevices: StateFlow<List<BtDevice>> = _pairedDevices.asStateFlow()

    init {
        refreshPairedDevices()
    }

    @SuppressLint("MissingPermission")
    fun refreshPairedDevices() {
        if (!PermissionHelper.hasBluetoothPermissions(context)) {
            Log.w(TAG, "Bluetooth permissions not granted")
            return
        }

        val adapter = bluetoothAdapter
        if (adapter == null || !adapter.isEnabled) {
            _pairedDevices.value = emptyList()
            return
        }

        try {
            val bonded = adapter.bondedDevices ?: emptySet()
            val list = bonded.map { device ->
                val profileType = detectProfileType(device)
                BtDevice(
                    address = device.address,
                    name = device.name ?: device.address,
                    profileType = profileType,
                    isConnected = false
                )
            }
            _pairedDevices.value = list
            Log.d(TAG, "Found ${list.size} paired Bluetooth devices")
        } catch (e: Exception) {
            Log.e(TAG, "Error listing bonded devices: ${e.message}")
        }
    }

    private fun detectProfileType(device: BluetoothDevice): BtProfileType {
        val btClass = device.bluetoothClass ?: return BtProfileType.AUDIO
        val deviceClass = btClass.deviceClass

        return when {
            deviceClass == BluetoothClass.Device.Major.PERIPHERAL ||
            deviceClass == 0x0504 || // Gamepad
            deviceClass == 0x0508 || // Joystick
            deviceClass == 0x0540 || // Keyboard
            deviceClass == 0x0580    // Mouse
            -> BtProfileType.HID

            btClass.hasService(BluetoothClass.Service.AUDIO) ||
            deviceClass == BluetoothClass.Device.AUDIO_VIDEO_HEADPHONES ||
            deviceClass == BluetoothClass.Device.AUDIO_VIDEO_WEARABLE_HEADSET ||
            deviceClass == BluetoothClass.Device.AUDIO_VIDEO_LOUDSPEAKER ||
            deviceClass == BluetoothClass.Device.AUDIO_VIDEO_HANDSFREE
            -> BtProfileType.AUDIO

            else -> BtProfileType.AUDIO
        }
    }

    companion object {
        private const val TAG = "BluetoothScanner"
    }
}
