package com.btbridge.repository

import com.btbridge.model.PcDevice
import com.btbridge.network.ControlClient
import com.btbridge.network.NsdDiscovery
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class NetworkRepository @Inject constructor(
    private val nsdDiscovery: NsdDiscovery,
    private val controlClient: ControlClient
) {
    val isConnected: StateFlow<Boolean> = controlClient.isConnected
    val latencyMs: StateFlow<Int> = controlClient.latencyMs

    fun discoverPcs(): Flow<List<PcDevice>> = nsdDiscovery.discoverServers()

    suspend fun connect(pcDevice: PcDevice): Boolean =
        controlClient.connect(pcDevice.host, pcDevice.port)

    suspend fun disconnect() =
        controlClient.disconnect()

    fun startAudioStream(mode: String = "a2dp") =
        controlClient.sendStartAudio(mode)

    fun stopAudioStream() =
        controlClient.sendStop()
}
