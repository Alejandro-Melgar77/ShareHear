package com.btbridge.bluetooth

import android.annotation.SuppressLint
import android.bluetooth.BluetoothA2dp
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.util.Log
import com.btbridge.util.PermissionHelper
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class A2dpManager @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
    val bluetoothAdapter: BluetoothAdapter? = bluetoothManager?.adapter

    private var a2dpProfile: BluetoothA2dp? = null

    private val _connectedDevice = MutableStateFlow<BluetoothDevice?>(null)
    val connectedDevice: StateFlow<BluetoothDevice?> = _connectedDevice.asStateFlow()

    private val _isA2dpConnected = MutableStateFlow(false)
    val isA2dpConnected: StateFlow<Boolean> = _isA2dpConnected.asStateFlow()

    private val profileListener = object : BluetoothProfile.ServiceListener {
        @SuppressLint("MissingPermission")
        override fun onServiceConnected(profile: Int, proxy: BluetoothProfile) {
            if (profile == BluetoothProfile.A2DP) {
                a2dpProfile = proxy as BluetoothA2dp
                Log.d(TAG, "A2DP Profile proxy connected")
                updateConnectedDevice()
            }
        }

        override fun onServiceDisconnected(profile: Int) {
            if (profile == BluetoothProfile.A2DP) {
                a2dpProfile = null
                _connectedDevice.value = null
                _isA2dpConnected.value = false
                Log.d(TAG, "A2DP Profile proxy disconnected")
            }
        }
    }

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context, intent: Intent) {
            if (intent.action == BluetoothA2dp.ACTION_CONNECTION_STATE_CHANGED) {
                val state = intent.getIntExtra(BluetoothProfile.EXTRA_STATE, BluetoothProfile.STATE_DISCONNECTED)
                val device = intent.getParcelableExtra<BluetoothDevice>(BluetoothDevice.EXTRA_DEVICE)
                Log.d(TAG, "A2DP connection state changed: $state for ${device?.address}")
                updateConnectedDevice()
            }
        }
    }

    init {
        initProfile()
        val filter = IntentFilter(BluetoothA2dp.ACTION_CONNECTION_STATE_CHANGED)
        context.registerReceiver(receiver, filter)
    }

    private fun initProfile() {
        bluetoothAdapter?.getProfileProxy(context, profileListener, BluetoothProfile.A2DP)
    }

    @SuppressLint("MissingPermission")
    fun updateConnectedDevice() {
        if (!PermissionHelper.hasBluetoothPermissions(context)) return

        val profile = a2dpProfile ?: return
        try {
            val connectedList = profile.connectedDevices
            if (connectedList.isNotEmpty()) {
                val active = connectedList.first()
                _connectedDevice.value = active
                _isA2dpConnected.value = true
                Log.i(TAG, "Active A2DP device: ${active.name} (${active.address})")
            } else {
                _connectedDevice.value = null
                _isA2dpConnected.value = false
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error checking A2DP connected devices: ${e.message}")
        }
    }

    fun cleanup() {
        try {
            context.unregisterReceiver(receiver)
        } catch (e: Exception) {
            Log.d(TAG, "Receiver already unregistered: ${e.message}")
        }
        if (a2dpProfile != null && bluetoothAdapter != null) {
            bluetoothAdapter.closeProfileProxy(BluetoothProfile.A2DP, a2dpProfile)
            a2dpProfile = null
        }
    }

    companion object {
        private const val TAG = "A2dpManager"
    }
}
