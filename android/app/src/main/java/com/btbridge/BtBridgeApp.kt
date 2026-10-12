package com.btbridge

import android.app.Application
import com.btbridge.service.BridgeNotification
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class BtBridgeApp : Application() {
    override fun onCreate() {
        super.onCreate()
        BridgeNotification.createChannel(this)
    }
}
