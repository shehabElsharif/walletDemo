package com.walletdemo

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.walletdemo.ui.screens.LoginScreen
import com.walletdemo.ui.screens.TopUpScreen
import com.walletdemo.ui.screens.WalletScreen
import com.walletdemo.ui.theme.WalletTheme
import com.walletdemo.viewmodel.AuthViewModel
import com.walletdemo.viewmodel.WalletViewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            WalletTheme {
                val navController = rememberNavController()
                val authViewModel: AuthViewModel = viewModel()
                val walletViewModel: WalletViewModel = viewModel()
                val authState by authViewModel.state.collectAsState()
                val walletState by walletViewModel.state.collectAsState()

                val startDest = if (authState.isAuthenticated) "wallet" else "login"

                NavHost(navController = navController, startDestination = startDest) {
                    composable("login") {
                        LoginScreen(
                            state = authState,
                            onLogin = { u, p -> authViewModel.login(u, p) },
                            onRegister = { u, p -> authViewModel.register(u, p) }
                        )
                        LaunchedEffect(authState.isAuthenticated) {
                            if (authState.isAuthenticated) {
                                navController.navigate("wallet") {
                                    popUpTo("login") { inclusive = true }
                                }
                            }
                        }
                    }

                    composable("wallet") {
                        LaunchedEffect(Unit) {
                            walletViewModel.connectWebSocket()
                            walletViewModel.loadBalance()
                        }
                        WalletScreen(
                            state = walletState,
                            username = authState.username ?: "",
                            onTopUp = { navController.navigate("topup") },
                            onRefresh = { walletViewModel.loadBalance() },
                            onLogout = {
                                walletViewModel.disconnectWebSocket()
                                walletViewModel.resetAuth()
                                authViewModel.logout()
                                navController.navigate("login") {
                                    popUpTo("wallet") { inclusive = true }
                                }
                            }
                        )
                    }

                    composable("topup") {
                        TopUpScreen(
                            state = walletState,
                            onTopUp = { amount, gateway, msisdn, birthYear, env ->
                                walletViewModel.topup(amount, gateway, msisdn, birthYear, env)
                            },
                            onConfirmOtp = { txnId, otp ->
                                walletViewModel.confirmOtp(txnId, otp)
                            },
                            onBack = {
                                walletViewModel.clearTopupResult()
                                navController.popBackStack()
                            },
                            onClearResult = { walletViewModel.clearTopupResult() }
                        )
                    }
                }
            }
        }
    }
}
