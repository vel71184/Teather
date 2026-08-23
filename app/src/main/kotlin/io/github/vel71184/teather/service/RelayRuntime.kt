package io.github.vel71184.teather.service

import android.content.Context
import android.util.Log
import io.github.vel71184.teather.network.AndroidNetworkConnector
import io.github.vel71184.teather.network.UpstreamPreference
import io.github.vel71184.teather.relay.RelayStats
import io.github.vel71184.teather.relay.RelayStatsSnapshot
import io.github.vel71184.teather.relay.Socks5Server

data class RelayConfiguration(
    val port: Int = DEFAULT_PORT,
    val upstream: UpstreamPreference = UpstreamPreference.CELLULAR,
) {
    init {
        require(port in 1024..65535) { "Relay port must be between 1024 and 65535" }
    }

    companion object {
        const val DEFAULT_PORT = 1080
    }
}

enum class RelayLifecycle {
    STOPPED,
    STARTING,
    RUNNING,
    FAILED,
}

data class RelayStatus(
    val lifecycle: RelayLifecycle,
    val configuration: RelayConfiguration?,
    val boundPort: Int?,
    val stats: RelayStatsSnapshot?,
    val failureCategory: String?,
)

object RelayRuntime {
    @Volatile
    private var lifecycle = RelayLifecycle.STOPPED

    @Volatile
    private var configuration: RelayConfiguration? = null

    @Volatile
    private var boundPort: Int? = null

    @Volatile
    private var failureCategory: String? = null

    @Volatile
    private var server: Socks5Server? = null

    @Synchronized
    fun start(context: Context, requested: RelayConfiguration): RelayStatus {
        stopLocked()
        lifecycle = RelayLifecycle.STARTING
        configuration = requested
        failureCategory = null

        return try {
            val stats = RelayStats()
            val connector = AndroidNetworkConnector(
                context = context,
                preference = requested.upstream,
                onSelected = stats::selectedUpstream,
            )
            val newServer = Socks5Server(
                port = requested.port,
                connector = connector,
                stats = stats,
                logger = { category -> Log.i(LOG_TAG, category) },
            )
            val actualPort = newServer.start()
            server = newServer
            boundPort = actualPort
            lifecycle = RelayLifecycle.RUNNING
            snapshot()
        } catch (error: Throwable) {
            Log.e(LOG_TAG, "relay.lifecycle.start-failed", error)
            failureCategory = error.javaClass.simpleName.ifBlank { "start-failed" }
            lifecycle = RelayLifecycle.FAILED
            server = null
            boundPort = null
            snapshot()
        }
    }

    @Synchronized
    fun stop(): RelayStatus {
        stopLocked()
        return snapshot()
    }

    fun snapshot(): RelayStatus = RelayStatus(
        lifecycle = lifecycle,
        configuration = configuration,
        boundPort = boundPort,
        stats = server?.stats?.snapshot(),
        failureCategory = failureCategory,
    )

    private fun stopLocked() {
        server?.close()
        server = null
        boundPort = null
        configuration = null
        failureCategory = null
        lifecycle = RelayLifecycle.STOPPED
    }

    private const val LOG_TAG = "Teather"
}
