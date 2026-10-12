package com.btbridge.model

data class PcDevice(
    val name: String,
    val host: String,
    val port: Int = 9001,
    val audioPort: Int = 5004,
    val os: String = "unknown"
)
