package com.btbridge.model

enum class BtProfileType {
    AUDIO,
    HID
}

data class BtDevice(
    val address: String,
    val name: String,
    val profileType: BtProfileType = BtProfileType.AUDIO,
    val isConnected: Boolean = false
)
