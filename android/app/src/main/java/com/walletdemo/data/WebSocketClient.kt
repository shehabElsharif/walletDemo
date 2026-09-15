package com.walletdemo.data

import com.google.gson.Gson
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.util.concurrent.TimeUnit

class WebSocketClient {
    private var webSocket: WebSocket? = null
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()
    private val gson = Gson()

    var onBalanceUpdated: ((balanceMinor: Int, balance: String) -> Unit)? = null
    var onConnected: (() -> Unit)? = null
    var onDisconnected: (() -> Unit)? = null

    fun connect(baseUrl: String, token: String) {
        if (webSocket != null) return
        val url = baseUrl.replace("http", "ws") + "/ws?token=$token"
        val request = Request.Builder().url(url).build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                onConnected?.invoke()
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                val message = gson.fromJson(text, WebSocketMessage::class.java)
                if (message.type == "balance_updated" && message.balanceMinor != null && message.balance != null) {
                    onBalanceUpdated?.invoke(message.balanceMinor, message.balance)
                }
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                webSocket.close(1000, null)
                onDisconnected?.invoke()
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                onDisconnected?.invoke()
            }
        })
    }

    fun disconnect() {
        webSocket?.close(1000, "User disconnecting")
        webSocket = null
    }
}
