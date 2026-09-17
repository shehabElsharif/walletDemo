package com.walletdemo.ui.screens

import android.os.Handler
import android.os.Looper
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.walletdemo.viewmodel.WalletState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TopUpScreen(
    state: WalletState,
    onTopUp: (Double, String, String?, String?, String) -> Unit,
    onConfirmOtp: (String, String) -> Unit,
    onBack: () -> Unit,
    onClearResult: () -> Unit
) {
    var amount by remember { mutableStateOf("") }
    var gateway by remember { mutableStateOf("sadad") }
    var msisdn by remember { mutableStateOf("") }
    var birthYear by remember { mutableStateOf("") }
    var otp by remember { mutableStateOf("") }
    var gatewayExpanded by remember { mutableStateOf(false) }
    var isProd by remember { mutableStateOf(false) }

    val topupResult = state.topupResult

    DisposableEffect(Unit) {
        onDispose { onClearResult() }
    }

    if (topupResult?.checkoutUrl != null) {
        BackHandler {
            onClearResult()
            onBack()
        }
        AndroidView(
            factory = { context ->
                val webView = WebView(context)
                val handler = Handler(Looper.getMainLooper())
                webView.webViewClient = object : WebViewClient() {
                    override fun shouldOverrideUrlLoading(view: WebView?, request: android.webkit.WebResourceRequest?): Boolean {
                        return false
                    }
                    override fun onPageFinished(view: WebView?, url: String?) {
                        super.onPageFinished(view, url)
                        view?.evaluateJavascript("""
                          (function checkPayment() {
                            const status = document.getElementById('status')?.textContent || '';
                            if (status.includes('Payment successful')) {
                              Android.paymentDone();
                            } else {
                              setTimeout(checkPayment, 1500);
                            }
                          })();
                        """, null)
                    }
                }
                webView.addJavascriptInterface(object : Any() {
                    @android.webkit.JavascriptInterface
                    fun paymentDone() {
                        handler.post {
                            onClearResult()
                            onBack()
                        }
                    }
                }, "Android")
                webView.settings.javaScriptEnabled = true
                webView.settings.domStorageEnabled = true
                webView.settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
                webView.settings.allowContentAccess = true
                webView.settings.databaseEnabled = true
                webView.settings.setSupportMultipleWindows(false)
                webView.settings.javaScriptCanOpenWindowsAutomatically = true
                webView.loadUrl(topupResult.checkoutUrl)
                webView
            },
            modifier = Modifier.fillMaxSize()
        )
        return
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        TextButton(onClick = {
            onClearResult()
            onBack()
        }) {
            Text("Back")
        }

        Spacer(modifier = Modifier.height(16.dp))

        if (topupResult?.needsOtp == true) {
            Text(
                text = "Enter OTP",
                style = MaterialTheme.typography.headlineSmall
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = when {
                    gateway == "edfali" && !isProd -> "Test mode: enter 1234."
                    else -> "Enter the OTP sent to your phone."
                },
                style = MaterialTheme.typography.bodyMedium
            )
            Spacer(modifier = Modifier.height(16.dp))

            OutlinedTextField(
                value = otp,
                onValueChange = { otp = it },
                label = { Text("OTP Code") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
            )

            Spacer(modifier = Modifier.height(16.dp))

            if (state.isLoading) {
                CircularProgressIndicator()
            } else {
                Button(
                    onClick = { onConfirmOtp(topupResult.transactionId!!, otp) },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = otp.isNotBlank()
                ) {
                    Text("Confirm Payment")
                }
            }
        } else {
            Text(
                text = "Top Up Wallet",
                style = MaterialTheme.typography.headlineSmall
            )
            Spacer(modifier = Modifier.height(16.dp))

            OutlinedTextField(
                value = amount,
                onValueChange = { amount = it },
                label = { Text("Amount (LYD)") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal)
            )

            Spacer(modifier = Modifier.height(12.dp))

            ExposedDropdownMenuBox(
                expanded = gatewayExpanded,
                onExpandedChange = { gatewayExpanded = it }
            ) {
                OutlinedTextField(
                    value = gateway.replaceFirstChar { it.uppercase() },
                    onValueChange = {},
                    label = { Text("Payment Gateway") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .menuAnchor(MenuAnchorType.PrimaryNotEditable),
                    readOnly = true,
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = gatewayExpanded) }
                )
                ExposedDropdownMenu(
                    expanded = gatewayExpanded,
                    onDismissRequest = { gatewayExpanded = false }
                ) {
                    DropdownMenuItem(
                        text = { Text("Sadad") },
                        onClick = { gateway = "sadad"; gatewayExpanded = false }
                    )
                    DropdownMenuItem(
                        text = { Text("Moamalat") },
                        onClick = { gateway = "moamalat"; gatewayExpanded = false }
                    )
                    DropdownMenuItem(
                        text = { Text("Edfali") },
                        onClick = { gateway = "edfali"; gatewayExpanded = false }
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text = "Test",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = if (!isProd) FontWeight.Bold else FontWeight.Normal
                )
                Spacer(modifier = Modifier.width(8.dp))
                Switch(
                    checked = isProd,
                    onCheckedChange = { isProd = it }
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Production",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = if (isProd) FontWeight.Bold else FontWeight.Normal,
                    color = if (isProd) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface
                )
            }

            if (isProd) {
                Text(
                    text = "Real payment will be processed. OTP is sent to your phone.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.padding(top = 4.dp)
                )
            }

            if (gateway in listOf("sadad", "edfali")) {
                Spacer(modifier = Modifier.height(12.dp))

                OutlinedTextField(
                    value = msisdn,
                    onValueChange = { msisdn = it },
                    label = { Text("Phone Number") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone)
                )
            }

            if (gateway == "sadad") {
                Spacer(modifier = Modifier.height(12.dp))

                OutlinedTextField(
                    value = birthYear,
                    onValueChange = { birthYear = it },
                    label = { Text("Birth Year") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            state.error?.let { error ->
                Text(
                    text = error,
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(bottom = 12.dp)
                )
            }

            if (state.isLoading) {
                CircularProgressIndicator()
            } else {
                Button(
                    onClick = {
                        val a = amount.toDoubleOrNull() ?: return@Button
                        val env = if (isProd) "prod" else "test"
                        onTopUp(a, gateway, msisdn.ifBlank { null }, birthYear.ifBlank { null }, env)
                    },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = amount.toDoubleOrNull() != null && amount.toDouble() > 0
                ) {
                    Text(if (isProd) "Pay Now (Production)" else "Pay Now (Test)")
                }
            }
        }
    }
}
