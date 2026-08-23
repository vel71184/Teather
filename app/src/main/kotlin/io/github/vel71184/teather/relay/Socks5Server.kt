package io.github.vel71184.teather.relay

import java.io.Closeable
import java.io.IOException
import java.net.ConnectException
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.NoRouteToHostException
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.CountDownLatch
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.Semaphore
import java.util.concurrent.ThreadFactory
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicLong

fun interface OutboundConnector {
    @Throws(IOException::class)
    fun connect(destination: SocksDestination, timeoutMs: Int): Socket
}

class Socks5Server(
    private val port: Int,
    private val connector: OutboundConnector,
    val stats: RelayStats = RelayStats(),
    private val maxConnections: Int = DEFAULT_MAX_CONNECTIONS,
    private val relayIdleTimeoutMs: Int = RELAY_IDLE_TIMEOUT_MS,
    private val idleCheckIntervalMs: Int = IDLE_CHECK_INTERVAL_MS,
    private val logger: (category: String) -> Unit = {},
) : Closeable {
    private val running = AtomicBoolean(false)
    private val connectionSlots = Semaphore(maxConnections)
    private val sockets = ConcurrentHashMap.newKeySet<Socket>()
    private val acceptExecutor = Executors.newSingleThreadExecutor(namedThreads("teather-accept"))
    private val sessionExecutor = Executors.newCachedThreadPool(namedThreads("teather-session"))
    private val transferExecutor = Executors.newCachedThreadPool(namedThreads("teather-transfer"))

    @Volatile
    private var serverSocket: ServerSocket? = null

    init {
        require(maxConnections > 0) { "Connection limit must be positive" }
        require(relayIdleTimeoutMs > 0) { "Relay idle timeout must be positive" }
        require(idleCheckIntervalMs > 0) { "Idle check interval must be positive" }
    }

    @Synchronized
    fun start(): Int {
        check(running.compareAndSet(false, true)) { "SOCKS server is already running" }
        try {
            val listener = ServerSocket()
            listener.reuseAddress = true
            listener.bind(InetSocketAddress(InetAddress.getByAddress(byteArrayOf(127, 0, 0, 1)), port))
            serverSocket = listener
            acceptExecutor.execute { acceptLoop(listener) }
            logger("relay.socks.started")
            return listener.localPort
        } catch (error: Throwable) {
            running.set(false)
            close()
            throw error
        }
    }

    private fun acceptLoop(listener: ServerSocket) {
        while (running.get()) {
            try {
                val client = listener.accept()
                client.tcpNoDelay = true
                stats.clientAccepted()
                if (!connectionSlots.tryAcquire()) {
                    stats.clientRejected("connection-limit")
                    logger("relay.socks.connection-limit")
                    client.closeQuietly()
                    continue
                }
                sockets.add(client)
                sessionExecutor.execute {
                    try {
                        handleClient(client)
                    } finally {
                        sockets.remove(client)
                        client.closeQuietly()
                        connectionSlots.release()
                    }
                }
            } catch (error: SocketException) {
                if (running.get()) {
                    stats.error("accept-socket")
                    logger("relay.socks.accept-socket")
                }
            } catch (error: IOException) {
                if (running.get()) {
                    stats.error("accept-io")
                    logger("relay.socks.accept-io")
                }
            }
        }
    }

    private fun handleClient(client: Socket) {
        var requestRead = false
        var replySent = false
        var sessionOpened = false
        var remote: Socket? = null
        try {
            client.soTimeout = HANDSHAKE_TIMEOUT_MS
            Socks5Protocol.negotiate(client.getInputStream(), client.getOutputStream())
            val destination = Socks5Protocol.readConnectRequest(client.getInputStream())
            requestRead = true

            remote = connector.connect(destination, CONNECT_TIMEOUT_MS)
            sockets.add(remote)
            remote.tcpNoDelay = true
            val readPollInterval = minOf(idleCheckIntervalMs, relayIdleTimeoutMs)
            remote.soTimeout = readPollInterval
            client.soTimeout = readPollInterval

            Socks5Protocol.writeReply(
                client.getOutputStream(),
                Socks5Protocol.REPLY_SUCCEEDED,
                remote.localSocketAddress as? InetSocketAddress,
            )
            replySent = true
            stats.sessionOpened()
            sessionOpened = true
            relayBidirectionally(client, remote)
        } catch (error: SocksProtocolException) {
            stats.clientRejected("protocol")
            logger("relay.socks.protocol")
            if (error.replyAllowed && !replySent) {
                writeFailureReply(client, error.replyCode)
            }
        } catch (error: IOException) {
            val category = errorCategory(error)
            stats.clientRejected(category)
            logger("relay.socks.$category")
            if (requestRead && !replySent) {
                writeFailureReply(client, replyCode(error))
            }
        } catch (error: RuntimeException) {
            stats.clientRejected("runtime")
            logger("relay.socks.runtime")
            if (requestRead && !replySent) {
                writeFailureReply(client, Socks5Protocol.REPLY_GENERAL_FAILURE)
            }
        } finally {
            if (sessionOpened) stats.sessionClosed()
            remote?.let {
                sockets.remove(it)
                it.closeQuietly()
            }
        }
    }

    private fun relayBidirectionally(client: Socket, remote: Socket) {
        val finished = CountDownLatch(2)
        val failed = AtomicBoolean(false)
        val lastActivityNanos = AtomicLong(System.nanoTime())

        transferExecutor.execute {
            pump(
                source = client,
                destination = remote,
                onBytes = stats::addClientToInternetBytes,
                failed = failed,
                finished = finished,
                lastActivityNanos = lastActivityNanos,
            )
        }
        transferExecutor.execute {
            pump(
                source = remote,
                destination = client,
                onBytes = stats::addInternetToClientBytes,
                failed = failed,
                finished = finished,
                lastActivityNanos = lastActivityNanos,
            )
        }

        try {
            finished.await()
        } catch (error: InterruptedException) {
            Thread.currentThread().interrupt()
            stats.error("relay-interrupted")
        }
    }

    private fun pump(
        source: Socket,
        destination: Socket,
        onBytes: (Int) -> Unit,
        failed: AtomicBoolean,
        finished: CountDownLatch,
        lastActivityNanos: AtomicLong,
    ) {
        try {
            val input = source.getInputStream()
            val output = destination.getOutputStream()
            val buffer = ByteArray(COPY_BUFFER_BYTES)
            while (running.get()) {
                val count = try {
                    input.read(buffer)
                } catch (error: SocketTimeoutException) {
                    val idleNanos = System.nanoTime() - lastActivityNanos.get()
                    if (idleNanos >= TimeUnit.MILLISECONDS.toNanos(relayIdleTimeoutMs.toLong())) {
                        throw error
                    }
                    continue
                }
                if (count < 0) break
                output.write(buffer, 0, count)
                output.flush()
                onBytes(count)
                lastActivityNanos.set(System.nanoTime())
            }
            destination.shutdownOutputQuietly()
        } catch (error: IOException) {
            if (running.get() && failed.compareAndSet(false, true)) {
                val category = errorCategory(error)
                stats.error(category)
                logger("relay.socks.$category")
                source.closeQuietly()
                destination.closeQuietly()
            }
        } finally {
            finished.countDown()
        }
    }

    private fun writeFailureReply(client: Socket, replyCode: Int) {
        try {
            Socks5Protocol.writeReply(client.getOutputStream(), replyCode)
        } catch (_: IOException) {
            // The peer may already be gone; the server still tears the socket down.
        }
    }

    override fun close() {
        running.set(false)
        serverSocket?.closeQuietly()
        sockets.toList().forEach { it.closeQuietly() }
        shutdown(acceptExecutor)
        shutdown(sessionExecutor)
        shutdown(transferExecutor)
        logger("relay.socks.stopped")
    }

    private fun shutdown(executor: ExecutorService) {
        executor.shutdownNow()
        try {
            executor.awaitTermination(250, TimeUnit.MILLISECONDS)
        } catch (_: InterruptedException) {
            Thread.currentThread().interrupt()
        }
    }

    private fun replyCode(error: IOException): Int = when (error) {
        is ConnectException -> Socks5Protocol.REPLY_CONNECTION_REFUSED
        is NoRouteToHostException -> Socks5Protocol.REPLY_NETWORK_UNREACHABLE
        is UnknownHostException -> Socks5Protocol.REPLY_HOST_UNREACHABLE
        is SocketTimeoutException -> Socks5Protocol.REPLY_TTL_EXPIRED
        else -> Socks5Protocol.REPLY_GENERAL_FAILURE
    }

    private fun errorCategory(error: IOException): String = when (error) {
        is ConnectException -> "connect-refused"
        is NoRouteToHostException -> "network-unreachable"
        is UnknownHostException -> "host-unreachable"
        is SocketTimeoutException -> "timeout"
        is SocketException -> "socket"
        else -> "io"
    }

    companion object {
        const val DEFAULT_MAX_CONNECTIONS = 64
        const val HANDSHAKE_TIMEOUT_MS = 10_000
        const val CONNECT_TIMEOUT_MS = 15_000
        const val RELAY_IDLE_TIMEOUT_MS = 300_000
        const val IDLE_CHECK_INTERVAL_MS = 30_000
        const val COPY_BUFFER_BYTES = 16 * 1024

        private fun namedThreads(prefix: String): ThreadFactory {
            val counter = AtomicInteger()
            return ThreadFactory { runnable ->
                Thread(runnable, "$prefix-${counter.incrementAndGet()}").apply {
                    isDaemon = true
                }
            }
        }

        private fun Closeable.closeQuietly() {
            try {
                close()
            } catch (_: IOException) {
                // Idempotent shutdown is more important than reporting a closed socket twice.
            }
        }

        private fun Socket.shutdownOutputQuietly() {
            try {
                if (!isClosed && !isOutputShutdown) shutdownOutput()
            } catch (_: IOException) {
                // A concurrent close is expected during relay shutdown.
            }
        }
    }
}
