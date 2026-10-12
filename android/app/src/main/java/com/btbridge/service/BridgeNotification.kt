package com.btbridge.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.btbridge.R
import com.btbridge.model.BridgeState
import com.btbridge.ui.MainActivity

object BridgeNotification {
    const val CHANNEL_ID = "btbridge_service_channel"
    const val NOTIFICATION_ID = 1001

    fun createChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = "BT Bridge Background Service"
            val descriptionText = "Mantiene activa la transmisión de audio por Bluetooth y red local"
            val importance = NotificationManager.IMPORTANCE_LOW
            val channel = NotificationChannel(CHANNEL_ID, name, importance).apply {
                description = descriptionText
                setShowBadge(false)
            }
            val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    fun buildNotification(
        context: Context,
        state: BridgeState,
        deviceName: String = "",
        pcName: String = "",
        latencyMs: Int = 0
    ): Notification {
        val openAppIntent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        val openAppPendingIntent = PendingIntent.getActivity(
            context,
            0,
            openAppIntent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val stopIntent = Intent(context, BridgeService::class.java).apply {
            action = BridgeService.ACTION_STOP
        }
        val stopPendingIntent = PendingIntent.getService(
            context,
            1,
            stopIntent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val title = when (state) {
            BridgeState.STREAMING -> "🎧 ShareHear — Transmitiendo"
            BridgeState.CONNECTED -> "🎧 ShareHear — Conectado"
            BridgeState.CONNECTING -> "🎧 ShareHear — Conectando..."
            else -> "🎧 ShareHear"
        }

        val contentText = if (deviceName.isNotBlank() && pcName.isNotBlank()) {
            "$deviceName → $pcName | ${latencyMs}ms"
        } else if (pcName.isNotBlank()) {
            "Conectado a $pcName | ${latencyMs}ms"
        } else {
            "Servicio activo en segundo plano"
        }

        return NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_media_play)
            .setContentTitle(title)
            .setContentText(contentText)
            .setContentIntent(openAppPendingIntent)
            .setOngoing(true)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Detener", stopPendingIntent)
            .build()
    }
}
