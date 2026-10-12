package com.btbridge.ui.viewmodel

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.btbridge.model.AudioMode
import com.btbridge.model.BridgeState
import com.btbridge.model.BridgeStatus
import com.btbridge.model.BtDevice
import com.btbridge.model.PcDevice
import com.btbridge.repository.BluetoothRepository
import com.btbridge.repository.NetworkRepository
import com.btbridge.service.BridgeService
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val networkRepository: NetworkRepository,
    private val bluetoothRepository: BluetoothRepository
) : ViewModel() {

    val bridgeStatus: StateFlow<BridgeStatus> = BridgeService.serviceStatus

    val discoveredPcs: StateFlow<List<PcDevice>> = networkRepository.discoverPcs()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val pairedDevices: StateFlow<List<BtDevice>> = bluetoothRepository.pairedDevices
    val selectedBtDevice: StateFlow<BtDevice?> = bluetoothRepository.selectedDevice

    private val _selectedPc = MutableStateFlow<PcDevice?>(null)
    val selectedPc: StateFlow<PcDevice?> = _selectedPc.asStateFlow()

    private val _audioMode = MutableStateFlow(AudioMode.A2DP)
    val audioMode: StateFlow<AudioMode> = _audioMode.asStateFlow()

    init {
        // Automatically select first discovered PC if none selected
        viewModelScope.launch {
            discoveredPcs.collect { pcs ->
                if (_selectedPc.value == null && pcs.isNotEmpty()) {
                    _selectedPc.value = pcs.first()
                }
            }
        }

        // Automatically select first paired BT device if none selected
        viewModelScope.launch {
            pairedDevices.collect { devs ->
                if (selectedBtDevice.value == null && devs.isNotEmpty()) {
                    bluetoothRepository.selectDevice(devs.first())
                }
            }
        }
    }

    fun selectPc(pc: PcDevice) {
        _selectedPc.value = pc
    }

    fun setAudioMode(mode: AudioMode) {
        _audioMode.value = mode
        if (mode == AudioMode.SCO) {
            bluetoothRepository.enableMicMode()
        } else {
            bluetoothRepository.disableMicMode()
        }
    }

    fun toggleBridge(context: Context) {
        val currentStatus = bridgeStatus.value
        if (currentStatus.state == BridgeState.STREAMING || currentStatus.state == BridgeState.CONNECTED || currentStatus.state == BridgeState.CONNECTING) {
            BridgeService.stopBridge(context)
        } else {
            val pc = _selectedPc.value
            if (pc != null) {
                val modeStr = if (_audioMode.value == AudioMode.SCO) "sco" else "a2dp"
                BridgeService.startBridge(
                    context = context,
                    pcDevice = pc,
                    btDevice = selectedBtDevice.value,
                    mode = modeStr
                )
            }
        }
    }

    fun refreshBluetooth() {
        bluetoothRepository.refreshDevices()
    }
}
