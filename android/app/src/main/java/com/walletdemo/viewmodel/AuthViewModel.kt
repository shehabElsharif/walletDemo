package com.walletdemo.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.walletdemo.data.ApiClient
import com.walletdemo.data.TokenStore
import com.walletdemo.data.LoginRequest
import com.walletdemo.data.RegisterRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

data class AuthState(
    val isLoading: Boolean = false,
    val isAuthenticated: Boolean = false,
    val error: String? = null,
    val username: String? = null
)

class AuthViewModel(application: Application) : AndroidViewModel(application) {
    private val tokenStore = TokenStore(application)

    private val _state = MutableStateFlow(AuthState())
    val state: StateFlow<AuthState> = _state

    init {
        viewModelScope.launch {
            val token = tokenStore.token.first()
            val username = tokenStore.username.first()
            if (token != null) {
                _state.value = AuthState(isAuthenticated = true, username = username)
            }
        }
    }

    fun register(username: String, password: String) {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null)
            try {
                val resp = ApiClient.api.register(RegisterRequest(username, password))
                if (resp.isSuccessful) {
                    val body = resp.body()!!
                    tokenStore.save(body.accessToken, username)
                    _state.value = AuthState(isAuthenticated = true, username = username)
                } else {
                    val msg = resp.errorBody()?.string() ?: "Registration failed"
                    _state.value = _state.value.copy(isLoading = false, error = msg)
                }
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message ?: "Network error")
            }
        }
    }

    fun login(username: String, password: String) {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null)
            try {
                val resp = ApiClient.api.login(LoginRequest(username, password))
                if (resp.isSuccessful) {
                    val body = resp.body()!!
                    tokenStore.save(body.accessToken, username)
                    _state.value = AuthState(isAuthenticated = true, username = username)
                } else {
                    val msg = resp.errorBody()?.string() ?: "Login failed"
                    _state.value = _state.value.copy(isLoading = false, error = msg)
                }
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message ?: "Network error")
            }
        }
    }

    fun logout() {
        viewModelScope.launch {
            tokenStore.clear()
            _state.value = AuthState()
        }
    }
}
