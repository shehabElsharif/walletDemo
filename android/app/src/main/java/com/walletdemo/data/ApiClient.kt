package com.walletdemo.data

import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST

interface WalletApi {
    @POST("api/auth/register")
    suspend fun register(@Body request: RegisterRequest): Response<TokenResponse>

    @POST("api/auth/login")
    suspend fun login(@Body request: LoginRequest): Response<TokenResponse>

    @GET("api/wallet")
    suspend fun getBalance(@Header("Authorization") token: String): Response<WalletResponse>

    @POST("api/wallet/topup")
    suspend fun topup(
        @Header("Authorization") token: String,
        @Body request: TopupRequest
    ): Response<TopupResponse>

    @POST("api/wallet/topup/confirm")
    suspend fun confirmTopup(
        @Header("Authorization") token: String,
        @Body request: TopupConfirmRequest
    ): Response<WalletResponse>
}

object ApiClient {
    // Change this to your backend server address
    private var baseUrl: String = "http://10.0.2.2:8000"

    fun setBaseUrl(url: String) {
        baseUrl = url
    }

    private val retrofit: Retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(baseUrl)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    val api: WalletApi by lazy {
        retrofit.create(WalletApi::class.java)
    }
}
