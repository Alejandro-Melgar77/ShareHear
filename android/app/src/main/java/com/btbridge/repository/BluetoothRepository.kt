package com.btbridge.repository

import com.btbridge.bluetooth.BluetoothController
import com.btbridge.bluetooth.BluetoothScanner
import com.btbridge.model.BtDevice
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class BluetoothRepository @Inject constructor(
    private val controller: BluetoothController,
    private val scanner: BluetoothScanner
) {
    val pairedDevices: StateFlow<List<BtDevice>> = scanner.pairedDevices
    val selectedDevice: StateFlow<BtDevice?> = controller.selectedDevice

    fun refreshDevices() {
        scanner.refreshPairedDevices()
    }

    fun selectDevice(device: BtDevice) {
        controller.selectDevice(device)
    }

    fun enableMicMode(): Boolean = controller.enableScoMode()
    fun disableMicMode() = controller.disableScoMode()
}
