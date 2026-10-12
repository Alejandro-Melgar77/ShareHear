package com.btbridge.network

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.net.wifi.WifiManager
import android.util.Log
import com.btbridge.model.PcDevice
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class NsdDiscovery @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val nsdManager = context.getSystemService(Context.NSD_SERVICE) as? NsdManager
    private val wifiManager = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
    private var multicastLock: WifiManager.MulticastLock? = null

    fun discoverServers(): Flow<List<PcDevice>> = callbackFlow {
        val discoveredDevices = mutableMapOf<String, PcDevice>()

        // Acquire MulticastLock to receive mDNS on Android WiFi
        try {
            multicastLock = wifiManager?.createMulticastLock("btbridge_multicast_lock")?.apply {
                setReferenceCounted(true)
                acquire()
            }
        } catch (e: Exception) {
            Log.w(TAG, "Could not acquire MulticastLock: ${e.message}")
        }

        val listener = object : NsdManager.DiscoveryListener {
            override fun onDiscoveryStarted(regType: String) {
                Log.d(TAG, "mDNS Service discovery started for $regType")
            }

            override fun onServiceFound(service: NsdServiceInfo) {
                Log.d(TAG, "mDNS Service found: ${service.serviceName}")
                // Resolve service details to obtain IP address and port
                nsdManager?.resolveService(service, object : NsdManager.ResolveListener {
                    override fun onResolveFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {
                        Log.w(TAG, "Resolve failed for ${serviceInfo.serviceName}: code $errorCode")
                    }

                    override fun onServiceResolved(resolvedInfo: NsdServiceInfo) {
                        val host = resolvedInfo.host?.hostAddress ?: return
                        val port = resolvedInfo.port
                        val name = resolvedInfo.serviceName

                        // Extract optional attributes
                        val audioPort = try {
                            val attr = resolvedInfo.attributes?.get("audio_port")
                            attr?.let { String(it).toIntOrNull() } ?: 5004
                        } catch (e: Exception) {
                            5004
                        }

                        val os = try {
                            val attr = resolvedInfo.attributes?.get("os")
                            attr?.let { String(it) } ?: "pc"
                        } catch (e: Exception) {
                            "pc"
                        }

                        val device = PcDevice(
                            name = name,
                            host = host,
                            port = port,
                            audioPort = audioPort,
                            os = os
                        )

                        discoveredDevices[name] = device
                        trySend(discoveredDevices.values.toList())
                    }
                })
            }

            override fun onServiceLost(service: NsdServiceInfo) {
                Log.d(TAG, "mDNS Service lost: ${service.serviceName}")
                discoveredDevices.remove(service.serviceName)
                trySend(discoveredDevices.values.toList())
            }

            override fun onDiscoveryStopped(serviceType: String) {
                Log.d(TAG, "Discovery stopped: $serviceType")
            }

            override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) {
                Log.e(TAG, "Discovery failed to start: Error code: $errorCode")
                close()
            }

            override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) {
                Log.e(TAG, "Discovery failed to stop: Error code: $errorCode")
            }
        }

        try {
            nsdManager?.discoverServices(SERVICE_TYPE, NsdManager.PROTOCOL_DNS_SD, listener)
        } catch (e: Exception) {
            Log.e(TAG, "Error starting service discovery: ${e.message}")
        }

        awaitClose {
            try {
                nsdManager?.stopServiceDiscovery(listener)
            } catch (e: Exception) {
                Log.d(TAG, "Error stopping discovery listener: ${e.message}")
            }
            try {
                if (multicastLock?.isHeld == true) {
                    multicastLock?.release()
                }
            } catch (e: Exception) {
                Log.d(TAG, "Error releasing MulticastLock: ${e.message}")
            }
        }
    }

    companion object {
        private const val TAG = "NsdDiscovery"
        private const val SERVICE_TYPE = "_btbridge._tcp."
    }
}
