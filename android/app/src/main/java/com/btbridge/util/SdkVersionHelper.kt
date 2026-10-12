package com.btbridge.util

import android.os.Build

object SdkVersionHelper {
    val isApi31Plus: Boolean
        get() = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S

    val isApi33Plus: Boolean
        get() = Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU

    val hasModernSco: Boolean
        get() = isApi31Plus

    val requiresNotificationPermission: Boolean
        get() = isApi33Plus

    val requiresNewBtPermissions: Boolean
        get() = isApi31Plus
}
