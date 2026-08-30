package io.github.vel71184.teather.relay

import java.io.BufferedInputStream
import java.io.Closeable
import java.io.EOFException
import java.io.IOException
import java.io.OutputStream
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Socket
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.concurrent.thread

/**
 * Terminates one `tun2proxy --udpgw-server` TCP stream on the phone: reads
 * [UdpGatewayProtocol] frames, forwards each datagram from a [DatagramSocket]
 * bound to the selected upstream, and frames replies back on the same stream.
 *
 * One datagram socket (plus one reader thread) per connection id. A connection
 * id that reappears with a new destination is torn down and rebuilt, so a reused
 * tun2proxy stream never leaks late packets from an old flow into a new one.
 * Idle connections close on their own.
 */
class UdpGatewayServer(
    /** Binds a fresh datagram socket to the chosen upstream before first use. */
    private val bindToUpstream: (DatagramSocket) -> Unit,
    /** Resolves a hostname on the chosen upstream, or null if it has no address. */
    private val resolveOnUpstream: (String) -> InetAddress?,
    private val onDatagram: (clientToInternet: Int, internetToClient: Int) -> Unit = { _, _ -> },
    private val logger: (category: String) -> Unit = {},
    private val idleTimeoutMs: Long = DEFAULT_IDLE_TIMEOUT_MS,
) {
    fun matches(destination: SocksDestination): Boolean =
        destination.port == SENTINEL_PORT && destination.address?.hostAddress == SENTINEL_HOST

    fun serve(client: Socket) {
        val connections = ConcurrentHashMap<Int, Connection>()
        val output = client.getOutputStream()
        try {
            client.soTimeout = 0
            val input = BufferedInputStream(client.getInputStream())
            while (true) {
                val packet = UdpGatewayProtocol.read(input)
                when {
                    packet.isKeepalive ->
                        UdpGatewayProtocol.write(output, UdpGatewayProtocol.keepalive(packet.connId))
                    packet.isData -> dispatch(packet, connections, output)
                    else -> Unit // a client ERR frame carries nothing to act on
                }
            }
        } catch (_: EOFException) {
            // tun2proxy closed the stream; normal.
        } catch (_: IOException) {
            logger("relay.udpgw.stream-io")
        } finally {
            connections.values.toList().forEach(Connection::close)
            try {
                client.close()
            } catch (_: IOException) {
            }
        }
    }

    // One stream reads its frames on a single thread, so dispatch is never
    // re-entered concurrently for the same connection map.
    private fun dispatch(
        packet: UdpGatewayProtocol.Packet,
        connections: ConcurrentHashMap<Int, Connection>,
        output: OutputStream,
    ) {
        val target = packet.target ?: return
        var connection = connections[packet.connId]
        if (connection != null && (connection.isClosed || connection.target != target)) {
            connection.close()
            connection = null
        }
        if (connection == null) {
            connection = try {
                Connection(packet.connId, target, output, connections).also(Connection::start)
            } catch (_: IOException) {
                logger("relay.udpgw.open")
                writeQuietly { UdpGatewayProtocol.write(output, UdpGatewayProtocol.error(packet.connId)) }
                return
            }
            connections[packet.connId] = connection
        }
        try {
            connection.forward(packet.data)
            onDatagram(packet.data.size, 0)
        } catch (_: IOException) {
            logger("relay.udpgw.send")
            connection.close()
            writeQuietly { UdpGatewayProtocol.write(output, UdpGatewayProtocol.error(packet.connId)) }
        }
    }

    private inline fun writeQuietly(block: () -> Unit) {
        try {
            block()
        } catch (_: IOException) {
        }
    }

    private inner class Connection(
        val connId: Int,
        val target: UdpGatewayProtocol.Target,
        private val output: OutputStream,
        private val owner: ConcurrentHashMap<Int, Connection>,
    ) : Closeable {
        private val socket = DatagramSocket()
        private val destination: InetSocketAddress = resolve(target)
        private val closed = AtomicBoolean(false)
        private val started = AtomicBoolean(false)
        @Volatile
        private var lastActivityNanos = System.nanoTime()

        val isClosed: Boolean get() = closed.get()

        init {
            bindToUpstream(socket)
            socket.soTimeout = IDLE_POLL_MS
        }

        fun start() {
            if (started.compareAndSet(false, true)) {
                thread(isDaemon = true, name = "teather-udpgw-$connId", block = ::readLoop)
            }
        }

        fun forward(data: ByteArray) {
            if (data.isEmpty()) return
            socket.send(DatagramPacket(data, data.size, destination))
            lastActivityNanos = System.nanoTime()
        }

        private fun readLoop() {
            val buffer = ByteArray(MAX_DATAGRAM)
            try {
                while (!socket.isClosed) {
                    val packet = DatagramPacket(buffer, buffer.size)
                    try {
                        socket.receive(packet)
                    } catch (_: SocketTimeoutException) {
                        val idleMs = (System.nanoTime() - lastActivityNanos) / 1_000_000
                        if (idleMs >= idleTimeoutMs) break else continue
                    } catch (_: IOException) {
                        break
                    }
                    val source = packet.socketAddress as? InetSocketAddress ?: destination
                    val payload = packet.data.copyOfRange(packet.offset, packet.offset + packet.length)
                    UdpGatewayProtocol.write(output, UdpGatewayProtocol.data(connId, source, payload))
                    onDatagram(0, payload.size)
                    lastActivityNanos = System.nanoTime()
                }
            } catch (_: IOException) {
                logger("relay.udpgw.recv")
            } finally {
                close()
            }
        }

        override fun close() {
            if (!closed.compareAndSet(false, true)) return
            try {
                socket.close()
            } catch (_: IOException) {
            }
            owner.remove(connId, this)
        }

        private fun resolve(target: UdpGatewayProtocol.Target): InetSocketAddress = when (target) {
            is UdpGatewayProtocol.Target.Ip -> target.socketAddress
            is UdpGatewayProtocol.Target.Domain -> {
                val address = try {
                    resolveOnUpstream(target.host)
                } catch (_: UnknownHostException) {
                    null
                } ?: throw UnknownHostException("no address for ${target.host} on the selected upstream")
                InetSocketAddress(address, target.port)
            }
        }
    }

    companion object {
        const val SENTINEL_HOST = "240.0.0.1"
        const val SENTINEL_PORT = 1
        const val DEFAULT_IDLE_TIMEOUT_MS = 30_000L
        private const val IDLE_POLL_MS = 5_000
        private const val MAX_DATAGRAM = 2048
    }
}
