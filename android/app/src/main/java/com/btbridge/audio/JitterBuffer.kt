package com.btbridge.audio

import java.util.ArrayDeque

class JitterBuffer(
    private val targetDelayFrames: Int = 2
) {
    private val queue = ArrayDeque<ByteArray>()
    private var isPrimed = false
    private var lastArrivalMs = 0L
    private var measuredJitterMs = 0L

    fun enqueue(payload: ByteArray) {
        val now = System.currentTimeMillis()
        if (lastArrivalMs > 0) {
            val delta = kotlin.math.abs(now - lastArrivalMs - 20) // expected 20ms pacing
            measuredJitterMs = (measuredJitterMs * 15 + delta) / 16
        }
        lastArrivalMs = now

        synchronized(queue) {
            // Drop oldest packets if queue gets excessively long (> 20 frames = 400ms)
            while (queue.size > 20) {
                queue.pollFirst()
            }
            queue.addLast(payload)
            if (queue.size >= targetDelayFrames) {
                isPrimed = true
            }
        }
    }

    fun dequeue(): ByteArray? {
        synchronized(queue) {
            if (!isPrimed) {
                if (queue.size >= targetDelayFrames) {
                    isPrimed = true
                } else {
                    return null
                }
            }
            val item = queue.pollFirst()
            if (item == null) {
                isPrimed = false // Buffer underflow; re-prime on subsequent packets
            }
            return item
        }
    }

    fun clear() {
        synchronized(queue) {
            queue.clear()
            isPrimed = false
            lastArrivalMs = 0L
            measuredJitterMs = 0L
        }
    }

    val size: Int
        get() = synchronized(queue) { queue.size }

    val jitterEstimateMs: Long
        get() = measuredJitterMs
}
