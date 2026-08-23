package io.github.vel71184.teather.relay

import java.io.DataInputStream
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.ServerSocket
import java.net.Socket
import java.io.IOException
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import kotlin.concurrent.thread
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Socks5ServerIntegrationTest {
    @Test
    fun `CONNECT relays bytes to a loopback TCP service`() {
        val loopback = InetAddress.getByAddress(byteArrayOf(127, 0, 0, 1))
        val echoListener = ServerSocket(0, 1, loopback)
        val echoDone = CountDownLatch(1)
        thread(name = "test-echo", isDaemon = true) {
            try {
                echoListener.accept().use { socket ->
                    val buffer = ByteArray(64)
                    val count = socket.getInputStream().read(buffer)
                    socket.getOutputStream().write(buffer, 0, count)
                    socket.getOutputStream().flush()
                }
            } finally {
                echoDone.countDown()
            }
        }

        val server = Socks5Server(
            port = 0,
            connector = OutboundConnector { destination, timeoutMs ->
                Socket().apply {
                    val address = destination.address ?: InetAddress.getByName(destination.host)
                    connect(InetSocketAddress(address, destination.port), timeoutMs)
                }
            },
        )
        val relayPort = server.start()

        try {
            Socket(loopback, relayPort).use { client ->
                client.soTimeout = 5_000
                val input = DataInputStream(client.getInputStream())
                val output = client.getOutputStream()

                output.write(byteArrayOf(0x05, 0x01, 0x00))
                output.flush()
                assertArrayEquals(byteArrayOf(0x05, 0x00), input.readBytes(2))

                val targetPort = echoListener.localPort
                output.write(
                    byteArrayOf(
                        0x05,
                        0x01,
                        0x00,
                        0x01,
                        127,
                        0,
                        0,
                        1,
                        ((targetPort ushr 8) and 0xff).toByte(),
                        (targetPort and 0xff).toByte(),
                    ),
                )
                output.flush()

                assertEquals(0x05, input.readUnsignedByte())
                assertEquals(Socks5Protocol.REPLY_SUCCEEDED, input.readUnsignedByte())
                input.readUnsignedByte()
                val addressType = input.readUnsignedByte()
                val addressLength = if (addressType == 0x04) 16 else 4
                input.readBytes(addressLength)
                input.readUnsignedShort()

                val payload = "teather-p0".toByteArray()
                output.write(payload)
                output.flush()
                assertArrayEquals(payload, input.readBytes(payload.size))
            }

            assertTrue(echoDone.await(5, TimeUnit.SECONDS))
            val stats = awaitTransferredBytes(server, "teather-p0".length.toLong())
            assertEquals(1L, stats.establishedSessions)
            assertEquals("teather-p0".length.toLong(), stats.bytesClientToInternet)
            assertEquals("teather-p0".length.toLong(), stats.bytesInternetToClient)
        } finally {
            server.close()
            echoListener.close()
        }
    }

    @Test
    fun `connection-wide idle timeout permits a one-way active stream`() {
        val loopback = InetAddress.getByAddress(byteArrayOf(127, 0, 0, 1))
        val streamListener = ServerSocket(0, 1, loopback)
        val streamDone = CountDownLatch(1)
        thread(name = "test-stream", isDaemon = true) {
            try {
                streamListener.accept().use { socket ->
                    repeat(8) { index ->
                        socket.getOutputStream().write(index)
                        socket.getOutputStream().flush()
                        Thread.sleep(40)
                    }
                }
            } catch (_: IOException) {
                // The assertion below detects a relay that closes the one-way stream early.
            } finally {
                streamDone.countDown()
            }
        }

        val server = Socks5Server(
            port = 0,
            connector = loopbackConnector(),
            relayIdleTimeoutMs = 120,
            idleCheckIntervalMs = 20,
        )
        val relayPort = server.start()

        try {
            Socket(loopback, relayPort).use { client ->
                client.soTimeout = 2_000
                val input = DataInputStream(client.getInputStream())
                connectThroughSocks(input, client, streamListener.localPort)
                val streamed = input.readBytes(8)
                assertArrayEquals(ByteArray(8) { it.toByte() }, streamed)
            }
            assertTrue(streamDone.await(2, TimeUnit.SECONDS))
        } finally {
            server.close()
            streamListener.close()
        }
    }

    private fun DataInputStream.readBytes(length: Int): ByteArray = ByteArray(length).also(::readFully)

    private fun loopbackConnector(): OutboundConnector = OutboundConnector { destination, timeoutMs ->
        Socket().apply {
            val address = destination.address ?: InetAddress.getByName(destination.host)
            connect(InetSocketAddress(address, destination.port), timeoutMs)
        }
    }

    private fun connectThroughSocks(input: DataInputStream, client: Socket, targetPort: Int) {
        val output = client.getOutputStream()
        output.write(byteArrayOf(0x05, 0x01, 0x00))
        output.flush()
        assertArrayEquals(byteArrayOf(0x05, 0x00), input.readBytes(2))
        output.write(
            byteArrayOf(
                0x05,
                0x01,
                0x00,
                0x01,
                127,
                0,
                0,
                1,
                ((targetPort ushr 8) and 0xff).toByte(),
                (targetPort and 0xff).toByte(),
            ),
        )
        output.flush()
        assertEquals(0x05, input.readUnsignedByte())
        assertEquals(Socks5Protocol.REPLY_SUCCEEDED, input.readUnsignedByte())
        input.readUnsignedByte()
        val addressType = input.readUnsignedByte()
        input.readBytes(if (addressType == 0x04) 16 else 4)
        input.readUnsignedShort()
    }

    private fun awaitTransferredBytes(server: Socks5Server, expected: Long): RelayStatsSnapshot {
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(2)
        var snapshot = server.stats.snapshot()
        while (
            (snapshot.bytesClientToInternet < expected || snapshot.bytesInternetToClient < expected) &&
            System.nanoTime() < deadline
        ) {
            Thread.sleep(10)
            snapshot = server.stats.snapshot()
        }
        return snapshot
    }
}
