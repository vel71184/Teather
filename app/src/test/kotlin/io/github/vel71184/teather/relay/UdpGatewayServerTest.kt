package io.github.vel71184.teather.relay

import java.io.DataInputStream
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.ServerSocket
import java.net.Socket
import kotlin.concurrent.thread
import org.junit.After
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class UdpGatewayServerTest {
    private val loopback = InetAddress.getByAddress(byteArrayOf(127, 0, 0, 1))
    private val closeables = mutableListOf<AutoCloseable>()

    @After
    fun tearDown() {
        closeables.forEach { runCatching { it.close() } }
    }

    /** A UDP service that replies "<tag>:<payload>" to whoever writes to it. */
    private fun echoService(tag: String): DatagramSocket {
        val socket = DatagramSocket(0, loopback).also(closeables::add)
        thread(isDaemon = true, name = "test-udp-echo-$tag") {
            val buffer = ByteArray(2048)
            while (!socket.isClosed) {
                val request = DatagramPacket(buffer, buffer.size)
                try {
                    socket.receive(request)
                } catch (_: Exception) {
                    break
                }
                val reply = "$tag:".toByteArray() + request.data.copyOf(request.length)
                socket.send(DatagramPacket(reply, reply.size, request.socketAddress))
            }
        }
        return socket
    }

    private fun startServer(): Pair<Socket, DataInputStream> {
        val listener = ServerSocket(0, 1, loopback).also(closeables::add)
        val server = UdpGatewayServer(
            bindToUpstream = { /* default (unbound) socket is fine on the test host */ },
            resolveOnUpstream = { host -> InetAddress.getByName(host) },
        )
        thread(isDaemon = true, name = "test-udpgw-serve") {
            server.serve(listener.accept())
        }
        val client = Socket(loopback, listener.localPort).also(closeables::add)
        client.soTimeout = 5_000
        return client to DataInputStream(client.getInputStream())
    }

    private fun dataFrame(connId: Int, dst: InetSocketAddress, payload: ByteArray) =
        UdpGatewayProtocol.Packet(UdpGatewayProtocol.FLAG_DATA, connId, UdpGatewayProtocol.Target.Ip(dst), payload)

    @Test
    fun `a datagram is forwarded to its destination and the reply is framed back`() {
        val echo = echoService("A")
        val (client, input) = startServer()
        val dst = InetSocketAddress(loopback, echo.localPort)

        UdpGatewayProtocol.write(client.getOutputStream(), dataFrame(5, dst, "ping".toByteArray()))

        val reply = UdpGatewayProtocol.read(input)
        assertTrue(reply.isData)
        assertEquals(5, reply.connId)
        assertArrayEquals("A:ping".toByteArray(), reply.data)
    }

    @Test
    fun `a keepalive is answered with a keepalive`() {
        val (client, input) = startServer()
        UdpGatewayProtocol.write(client.getOutputStream(), UdpGatewayProtocol.keepalive(99))
        val reply = UdpGatewayProtocol.read(input)
        assertTrue(reply.isKeepalive)
        assertEquals(99, reply.connId)
    }

    @Test
    fun `reusing a connection id for a new destination rebuilds the socket`() {
        val echoA = echoService("A")
        val echoB = echoService("B")
        val (client, input) = startServer()

        UdpGatewayProtocol.write(
            client.getOutputStream(),
            dataFrame(1, InetSocketAddress(loopback, echoA.localPort), "x".toByteArray()),
        )
        assertArrayEquals("A:x".toByteArray(), UdpGatewayProtocol.read(input).data)

        UdpGatewayProtocol.write(
            client.getOutputStream(),
            dataFrame(1, InetSocketAddress(loopback, echoB.localPort), "y".toByteArray()),
        )
        assertArrayEquals("B:y".toByteArray(), UdpGatewayProtocol.read(input).data)
    }
}
