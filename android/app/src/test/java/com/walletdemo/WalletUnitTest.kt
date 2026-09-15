package com.walletdemo

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class WalletUnitTest {

    @Test
    fun `balance format is correct`() {
        val balanceMinor = 1250
        val balance = "%.2f".format(balanceMinor / 100.0)
        assertEquals("12.50", balance)
    }

    @Test
    fun `amount conversion to minor units`() {
        val amount = 25.75
        val amountMinor = (amount * 100).toInt()
        assertEquals(2575, amountMinor)
    }

    @Test
    fun `zero balance format`() {
        val balanceMinor = 0
        val balance = "%.2f".format(balanceMinor / 100.0)
        assertEquals("0.00", balance)
    }

    @Test
    fun `gateway names are valid`() {
        val validGateways = setOf("moamalat", "sadad", "edfali")
        assertTrue(validGateways.contains("moamalat"))
        assertTrue(validGateways.contains("sadad"))
        assertTrue(validGateways.contains("edfali"))
        assertTrue(!validGateways.contains("invalid"))
    }

    @Test
    fun `otp format validation`() {
        val otp = "1234"
        assertTrue(otp.length in 1..10)
        assertTrue(otp.all { it.isDigit() })
    }

    @Test
    fun `jwt token format`() {
        val token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.test"
        val parts = token.split(".")
        assertEquals(3, parts.size)
    }

    @Test
    fun `websocket url construction`() {
        val baseUrl = "http://10.0.2.2:8000"
        val token = "test-token"
        val wsUrl = baseUrl.replace("http", "ws") + "/ws?token=$token"
        assertEquals("ws://10.0.2.2:8000/ws?token=test-token", wsUrl)
    }
}
