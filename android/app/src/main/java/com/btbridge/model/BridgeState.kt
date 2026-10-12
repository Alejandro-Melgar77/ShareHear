package com.btbridge.model

enum class BridgeState {
    IDLE,
    DISCOVERING,
    CONNECTING,
    CONNECTED,
    STREAMING,
    ERROR
}

data class BridgeStatus(
    val state: BridgeState = BridgeState.IDLE,
    val pcDevice: PcDevice? = null,
    val btDevice: BtDevice? = null,
    val latencyMs: Int = 0,
    val errorMessage: String? = null
)
