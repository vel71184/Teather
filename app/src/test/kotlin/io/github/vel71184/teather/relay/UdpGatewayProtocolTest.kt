package io.github.vel71184.teather.relay

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.EOFException
import java.net.InetAddress
import java.net.InetSocketAddress
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class UdpGatewayProtocolTest {
    private fun roundTrip(packet: UdpGatewayProtocol.Packet): UdpGatewayProtocol.Packet {
        val out = ByteArrayOutputStream()
        UdpGatewayProtocol.write(out, packet)
        return UdpGatewayProtocol.read(ByteArrayInputStream(out.toByteArray()))
    }

    @Test
    fun `data frame with an IPv4 target round-trips`() {
        val source = InetSocketAddress(InetAddress.getByName("203.0.113.7"), 4433)
        val packet = UdpGatewayProtocol.data(0x1234, source, byteArrayOf(1, 2, 3, 4, 5))
        val decoded = roundTrip(packet)
        assertEquals(UdpGatewayProtocol.FLAG_DATA, decoded.flags)
        assertEquals(0x1234, decoded.connId)
        assertEquals(UdpGatewayProtocol.Target.Ip(source), decoded.target)
        assertArrayEquals(byteArrayOf(1, 2, 3, 4, 5), decoded.data)
    }

    @Test
    fun `data frame with an IPv6 target round-trips`() {
        val source = InetSocketAddress(InetAddress.getByName("2001:db8::1"), 53)
        val decoded = roundTrip(UdpGatewayProtocol.data(7, source, byteArrayOf(9)))
        assertEquals(UdpGatewayProtocol.Target.Ip(source), decoded.target)
        assertArrayEquals(byteArrayOf(9), decoded.data)
    }

    @Test
    fun `data frame with a domain target round-trips`() {
        val out = ByteArrayOutputStream()
        UdpGatewayProtocol.write(
            out,
            UdpGatewayProtocol.Packet(
                UdpGatewayProtocol.FLAG_DATA,
                42,
                UdpGatewayProtocol.Target.Domain("shadow.example.net", 9975),
                byteArrayOf(0x7f),
            ),
        )
        val decoded = UdpGatewayProtocol.read(ByteArrayInputStream(out.toByteArray()))
        assertEquals(UdpGatewayProtocol.Target.Domain("shadow.example.net", 9975), decoded.target)
        assertArrayEquals(byteArrayOf(0x7f), decoded.data)
    }

    @Test
    fun `keepalive frame carries no address or data`() {
        val decoded = roundTrip(UdpGatewayProtocol.keepalive(0xABCD))
        assertTrue(decoded.isKeepalive)
        assertEquals(0xABCD, decoded.connId)
        assertEquals(null, decoded.target)
        assertEquals(0, decoded.data.size)
    }

    @Test
    fun `length prefix counts every byte after itself`() {
        val out = ByteArrayOutputStream()
        UdpGatewayProtocol.write(out, UdpGatewayProtocol.keepalive(1))
        val bytes = out.toByteArray()
        val declared = ((bytes[0].toInt() and 0xff) shl 8) or (bytes[1].toInt() and 0xff)
        assertEquals(bytes.size - 2, declared)
        assertEquals(3, declared) // flags(1) + conn_id(2)
    }

    @Test
    fun `a clean end of stream reports EOF`() {
        assertThrows(EOFException::class.java) {
            UdpGatewayProtocol.read(ByteArrayInputStream(ByteArray(0)))
        }
    }

    @Test
    fun `an out-of-range length is rejected`() {
        assertThrows(java.io.IOException::class.java) {
            UdpGatewayProtocol.read(ByteArrayInputStream(byteArrayOf(0x00, 0x00)))
        }
    }

    @Test
    fun `a data frame with a truncated address block is an IOException not a crash`() {
        // LEN=4, flags=DATA, conn_id=0x0001, ATYP=IPv4 but no address/port bytes.
        val frame = byteArrayOf(0x00, 0x04, UdpGatewayProtocol.FLAG_DATA.toByte(), 0x00, 0x01, 0x01)
        assertThrows(java.io.IOException::class.java) {
            UdpGatewayProtocol.read(ByteArrayInputStream(frame))
        }
    }

    @Test
    fun `a data frame with a domain length past the frame end is an IOException`() {
        // LEN=6; body = flags(DATA), conn_id(2), ATYP=domain, domain-len=0x40
        // (claims 64 bytes that are not there), one trailing byte.
        val frame = byteArrayOf(
            0x00, 0x06, UdpGatewayProtocol.FLAG_DATA.toByte(), 0x00, 0x00, 0x03, 0x40, 0x00,
        )
        assertThrows(java.io.IOException::class.java) {
            UdpGatewayProtocol.read(ByteArrayInputStream(frame))
        }
    }
}
