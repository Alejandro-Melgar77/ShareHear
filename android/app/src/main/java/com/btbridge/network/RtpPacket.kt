package com.btbridge.network

import java.nio.ByteBuffer
import java.nio.ByteOrder

data class RtpPacket(
    val payloadType: Byte,
    val sequenceNumber: Int,
    val timestamp: Long,
    val ssrc: Long = SSRC,
    val payload: ByteArray
) {
    companion object {
        const val SSRC = 0x42544252L // 'BTBR'
        const val HEADER_SIZE = 12

        fun fromBytes(data: ByteArray, length: Int = data.size): RtpPacket? {
            if (length < HEADER_SIZE) return null

            val buf = ByteBuffer.wrap(data, 0, length).order(ByteOrder.BIG_ENDIAN)
            buf.get() // V, P, X, CC
            val pt = (buf.get().toInt() and 0x7F).toByte()
            val seq = buf.short.toInt() and 0xFFFF
            val ts = buf.int.toLong() and 0xFFFFFFFFL
            val ssrc = buf.int.toLong() and 0xFFFFFFFFL

            val payloadLength = length - HEADER_SIZE
            val payload = ByteArray(payloadLength)
            System.arraycopy(data, HEADER_SIZE, payload, 0, payloadLength)

            return RtpPacket(pt, seq, ts, ssrc, payload)
        }
    }

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false

        other as RtpPacket

        if (payloadType != other.payloadType) return false
        if (sequenceNumber != other.sequenceNumber) return false
        if (timestamp != other.timestamp) return false
        if (ssrc != other.ssrc) return false
        if (!payload.contentEquals(other.payload)) return false

        return true
    }

    override fun hashCode(): Int {
        var result = payloadType.toInt()
        result = 31 * result + sequenceNumber
        result = 31 * result + timestamp.hashCode()
        result = 31 * result + ssrc.hashCode()
        result = 31 * result + payload.contentHashCode()
        return result
    }
}
