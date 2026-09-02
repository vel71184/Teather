package io.github.vel71184.teather.relay

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.fail
import org.junit.Test

class Socks5ProtocolTest {
    @Test
    fun `negotiation selects no-auth when offered`() {
        val input = ByteArrayInputStream(byteArrayOf(0x05, 0x02, 0x02, 0x00))
        val output = ByteArrayOutputStream()

        Socks5Protocol.negotiate(input, output)

        assertArrayEquals(byteArrayOf(0x05, 0x00), output.toByteArray())
    }

    @Test
    fun `negotiation rejects unsupported authentication methods`() {
        val input = ByteArrayInputStream(byteArrayOf(0x05, 0x01, 0x02))
        val output = ByteArrayOutputStream()

        try {
            Socks5Protocol.negotiate(input, output)
            fail("Expected protocol failure")
        } catch (error: SocksProtocolException) {
            assertFalse(error.replyAllowed)
        }

        assertArrayEquals(byteArrayOf(0x05, 0xff.toByte()), output.toByteArray())
    }

    @Test
    fun `negotiation with a secret accepts the matching password`() {
        val secret = "00112233445566778899aabbccddeeff"
        val pass = secret.toByteArray(Charsets.US_ASCII)
        val input = ByteArrayInputStream(
            byteArrayOf(0x05, 0x01, 0x02) + // one method: username/password
                byteArrayOf(0x01, 0x04) + "user".toByteArray() +
                byteArrayOf(pass.size.toByte()) + pass,
        )
        val output = ByteArrayOutputStream()

        Socks5Protocol.negotiate(input, output, secret)

        assertArrayEquals(byteArrayOf(0x05, 0x02, 0x01, 0x00), output.toByteArray())
    }

    @Test
    fun `negotiation with a secret rejects a wrong password`() {
        val bad = "deadbeef".toByteArray(Charsets.US_ASCII)
        val input = ByteArrayInputStream(
            byteArrayOf(0x05, 0x01, 0x02) +
                byteArrayOf(0x01, 0x01) + "x".toByteArray() +
                byteArrayOf(bad.size.toByte()) + bad,
        )
        val output = ByteArrayOutputStream()

        try {
            Socks5Protocol.negotiate(input, output, "00112233445566778899aabbccddeeff")
            fail("Expected authentication failure")
        } catch (error: SocksProtocolException) {
            assertFalse(error.replyAllowed)
        }
        assertArrayEquals(byteArrayOf(0x05, 0x02, 0x01, 0x01), output.toByteArray())
    }

    @Test
    fun `negotiation with a secret refuses a client that only offers no-auth`() {
        val input = ByteArrayInputStream(byteArrayOf(0x05, 0x01, 0x00))
        val output = ByteArrayOutputStream()

        try {
            Socks5Protocol.negotiate(input, output, "00112233445566778899aabbccddeeff")
            fail("Expected method rejection")
        } catch (error: SocksProtocolException) {
            assertFalse(error.replyAllowed)
        }
        assertArrayEquals(byteArrayOf(0x05, 0xff.toByte()), output.toByteArray())
    }

    @Test
    fun `connect request parses domain and port`() {
        val host = "example.com".toByteArray(Charsets.US_ASCII)
        val request = byteArrayOf(0x05, 0x01, 0x00, 0x03, host.size.toByte()) +
            host + byteArrayOf(0x01, 0xbb.toByte())

        val destination = Socks5Protocol.readConnectRequest(ByteArrayInputStream(request))

        assertEquals("example.com", destination.host)
        assertEquals(null, destination.address)
        assertEquals(443, destination.port)
    }

    @Test
    fun `connect request rejects UDP associate`() {
        val request = byteArrayOf(
            0x05,
            0x03,
            0x00,
            0x01,
            127,
            0,
            0,
            1,
            0x00,
            0x35,
        )

        try {
            Socks5Protocol.readConnectRequest(ByteArrayInputStream(request))
            fail("Expected command rejection")
        } catch (error: SocksProtocolException) {
            assertEquals(Socks5Protocol.REPLY_COMMAND_NOT_SUPPORTED, error.replyCode)
        }
    }
}
