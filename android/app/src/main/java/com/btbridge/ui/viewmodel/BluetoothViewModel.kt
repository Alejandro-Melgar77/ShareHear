package com.btbridge.ui.viewmodel

import androidx.lifecycle.ViewModel
import com.btbridge.model.BtDevice
import com.btbridge.repository.BluetoothRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject

@HiltViewModel
class BluetoothViewModel @Inject constructor(
    private val bluetoothRepository: BluetoothRepository
) : ViewModel() {

    val pairedDevices: StateFlow<List<BtDevice>> = bluetoothRepository.pairedDevices
    val selectedDevice: StateFlow<BtDevice?> = bluetoothRepository.selectedDevice

    fun refreshDevices() {
        bluetoothRepository.refreshDevices()
    }

    fun selectDevice(device: BtDevice) {
        bluetoothRepository.selectDevice(device)
    }
}
