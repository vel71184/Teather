package io.github.vel71184.teather.service

import android.content.Context
import android.util.Log
import io.github.vel71184.teather.network.AndroidNetworkConnector
import io.github.vel71184.teather.network.NetworkSelector
import io.github.vel71184.teather.network.UpstreamPreference
import io.github.vel71184.teather.relay.RelayStats
import io.github.vel71184.teather.relay.RelayStatsSnapshot
import io.github.vel71184.teather.relay.Socks5Server
import io.github.vel71184.teather.relay.UdpGatewayServer
import java.security.SecureRandom

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
    val controlError: String? = null,
    /**
     * Per-run secret the desktop client authenticates the SOCKS connection with.
     * Only ever surfaced through the DUMP-protected relay status, so a local app
     * without adb/root cannot learn it. Null while stopped.
     */
    val secret: String? = null,
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
    private var controlError: String? = null

    @Volatile
    private var server: Socks5Server? = null

    @Volatile
    private var networks: NetworkSelector? = null

    @Volatile
    private var secret: String? = null

    @Synchronized
    fun start(context: Context, requested: RelayConfiguration): RelayStatus {
        when (RelayStartPolicy.decide(lifecycle, configuration, requested)) {
            RelayStartDecision.ATTACH -> {
                controlError = null
                return snapshot()
            }
            RelayStartDecision.REFUSE_MISMATCH -> {
                controlError = "incompatible-configuration"
                return snapshot()
            }
            RelayStartDecision.START -> Unit
        }
        stopLocked()
        lifecycle = RelayLifecycle.STARTING
        configuration = requested
        failureCategory = null
        controlError = null
        secret = newSecret()

        return try {
            val stats = RelayStats()
            val selector = NetworkSelector(context, requested.upstream)
            val connector = AndroidNetworkConnector(
                networks = selector,
                onSelected = stats::selectedUpstream,
            )
            val udpGateway = UdpGatewayServer(
                bindToUpstream = { udp -> selector.select().network.bindSocket(udp) },
                resolveOnUpstream = { host -> selector.select().network.getByName(host) },
                onDatagram = { clientToInternet, internetToClient ->
                    if (clientToInternet > 0) stats.addClientToInternetBytes(clientToInternet)
                    if (internetToClient > 0) stats.addInternetToClientBytes(internetToClient)
                },
                logger = { category -> Log.i(LOG_TAG, category) },
            )
            val newServer = Socks5Server(
                port = requested.port,
                connector = connector,
                stats = stats,
                udpGateway = udpGateway,
                secret = secret,
                logger = { category -> Log.i(LOG_TAG, category) },
            )
            val actualPort = newServer.start()
            server = newServer
            this.networks = selector
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

    /**
     * Apply [requested] to a running relay without dropping the listener. An
     * upstream-only change is a live rebind — established sessions stay on their
     * transport, new ones use the new one, and no client sees a gap. A port
     * change or a stopped relay falls back to a full (re)start.
     */
    @Synchronized
    fun reconfigure(context: Context, requested: RelayConfiguration): RelayStatus {
        val current = configuration
        if (lifecycle != RelayLifecycle.RUNNING || current == null) {
            return start(context, requested)
        }
        if (current.port != requested.port) {
            stopLocked()
            return start(context, requested)
        }
        if (current == requested) {
            controlError = null
            return snapshot()
        }
        networks?.rebind(requested.upstream)
        configuration = requested
        controlError = null
        Log.i(LOG_TAG, "relay.lifecycle.reconfigured")
        return snapshot()
    }

    fun snapshot(): RelayStatus = RelayStatus(
        lifecycle = lifecycle,
        configuration = configuration,
        boundPort = boundPort,
        stats = server?.stats?.snapshot(),
        failureCategory = failureCategory,
        controlError = controlError,
        secret = secret,
    )

    private fun stopLocked() {
        server?.close()
        server = null
        networks = null
        boundPort = null
        configuration = null
        failureCategory = null
        controlError = null
        secret = null
        lifecycle = RelayLifecycle.STOPPED
    }

    private fun newSecret(): String {
        val bytes = ByteArray(16)
        SecureRandom().nextBytes(bytes)
        return bytes.joinToString("") { "%02x".format(it.toInt() and 0xff) }
    }

    private const val LOG_TAG = "Teather"
}

enum class RelayStartDecision {
    START,
    ATTACH,
    REFUSE_MISMATCH,
}

object RelayStartPolicy {
    fun decide(
        lifecycle: RelayLifecycle,
        current: RelayConfiguration?,
        requested: RelayConfiguration,
    ): RelayStartDecision = when {
        lifecycle != RelayLifecycle.RUNNING -> RelayStartDecision.START
        current == requested -> RelayStartDecision.ATTACH
        else -> RelayStartDecision.REFUSE_MISMATCH
    }
}
