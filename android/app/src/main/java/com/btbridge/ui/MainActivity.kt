package com.btbridge.ui

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.btbridge.ui.screens.BluetoothScreen
import com.btbridge.ui.screens.HomeScreen
import com.btbridge.ui.theme.BtBridgeTheme
import com.btbridge.ui.viewmodel.BluetoothViewModel
import com.btbridge.ui.viewmodel.HomeViewModel
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            BtBridgeTheme {
                val navController = rememberNavController()

                NavHost(navController = navController, startDestination = "home") {
                    composable("home") {
                        val homeViewModel: HomeViewModel = hiltViewModel()
                        HomeScreen(
                            navController = navController,
                            viewModel = homeViewModel
                        )
                    }
                    composable("bluetooth") {
                        val bluetoothViewModel: BluetoothViewModel = hiltViewModel()
                        BluetoothScreen(
                            navController = navController,
                            viewModel = bluetoothViewModel
                        )
                    }
                }
            }
        }
    }
}
