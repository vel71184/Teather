package io.github.vel71184.teather.relay

import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.atomic.AtomicReference

data class RelayStatsSnapshot(
    val acceptedClients: Long,
    val establishedSessions: Long,
    val rejectedClients: Long,
    val activeSessions: Int,
    val bytesClientToInternet: Long,
    val bytesInternetToClient: Long,
    val lastUpstream: String?,
    val lastErrorCategory: String?,
    val startedAtEpochMs: Long,
)

class RelayStats {
    private val acceptedClients = AtomicLong()
    private val establishedSessions = AtomicLong()
    private val rejectedClients = AtomicLong()
    private val activeSessions = AtomicInteger()
    private val bytesClientToInternet = AtomicLong()
    private val bytesInternetToClient = AtomicLong()
    private val lastUpstream = AtomicReference<String?>(null)
    private val lastErrorCategory = AtomicReference<String?>(null)
    private val startedAtEpochMs = System.currentTimeMillis()

    fun clientAccepted() {
        acceptedClients.incrementAndGet()
    }

    fun clientRejected(category: String) {
        rejectedClients.incrementAndGet()
        lastErrorCategory.set(category)
    }

    fun sessionOpened() {
        establishedSessions.incrementAndGet()
        activeSessions.incrementAndGet()
    }

    fun sessionClosed() {
        activeSessions.updateAndGet { current -> (current - 1).coerceAtLeast(0) }
    }

    fun addClientToInternetBytes(count: Int) {
        bytesClientToInternet.addAndGet(count.toLong())
    }

    fun addInternetToClientBytes(count: Int) {
        bytesInternetToClient.addAndGet(count.toLong())
    }

    fun selectedUpstream(label: String) {
        lastUpstream.set(label)
    }

    fun error(category: String) {
        lastErrorCategory.set(category)
    }

    fun snapshot(): RelayStatsSnapshot = RelayStatsSnapshot(
        acceptedClients = acceptedClients.get(),
        establishedSessions = establishedSessions.get(),
        rejectedClients = rejectedClients.get(),
        activeSessions = activeSessions.get(),
        bytesClientToInternet = bytesClientToInternet.get(),
        bytesInternetToClient = bytesInternetToClient.get(),
        lastUpstream = lastUpstream.get(),
        lastErrorCategory = lastErrorCategory.get(),
        startedAtEpochMs = startedAtEpochMs,
    )
}
