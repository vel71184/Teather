package io.github.vel71184.teather.service

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities

data class CellularStatus(
    val available: Boolean,
    val validated: Boolean,
)

object AndroidRelayStatus {
    @Suppress("DEPRECATION")
    fun cellularStatus(context: Context): CellularStatus {
        val manager = context.getSystemService(ConnectivityManager::class.java)
        var available = false
        var validated = false
        manager.allNetworks.forEach { network ->
            val capabilities = manager.getNetworkCapabilities(network) ?: return@forEach
            if (
                capabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) &&
                capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            ) {
                available = true
                validated = validated || capabilities.hasCapability(
                    NetworkCapabilities.NET_CAPABILITY_VALIDATED,
                )
            }
        }
        return CellularStatus(available, validated)
    }
}

/** Stable line-oriented status consumed by the P1 desktop client. */
object RelayStatusWire {
    // 2: the relay now requires SOCKS username/password auth and publishes the
    // per-run secret here, so a desktop client that predates the auth handshake
    // must not attach.
    const val SCHEMA_VERSION = 2

    fun serialize(status: RelayStatus, cellular: CellularStatus): String = buildString {
        appendLine("teather.status.version=$SCHEMA_VERSION")
        appendLine("teather.status.secret=${status.secret ?: "none"}")
        appendLine("lifecycle=${status.lifecycle.name.lowercase()}")
        appendLine("bound_port=${status.boundPort ?: 0}")
        appendLine("configured_port=${status.configuration?.port ?: 0}")
        appendLine("configured_upstream=${status.configuration?.upstream?.wireName ?: "none"}")
        appendLine("selected_upstream=${clean(status.stats?.lastUpstream)}")
        appendLine("cellular_available=${cellular.available}")
        appendLine("cellular_validated=${cellular.validated}")
        appendLine("accepted_clients=${status.stats?.acceptedClients ?: 0}")
        appendLine("established_sessions=${status.stats?.establishedSessions ?: 0}")
        appendLine("rejected_clients=${status.stats?.rejectedClients ?: 0}")
        appendLine("active_sessions=${status.stats?.activeSessions ?: 0}")
        appendLine("bytes_client_to_internet=${status.stats?.bytesClientToInternet ?: 0}")
        appendLine("bytes_internet_to_client=${status.stats?.bytesInternetToClient ?: 0}")
        appendLine("failure_category=${clean(status.failureCategory)}")
        appendLine("last_error_category=${clean(status.stats?.lastErrorCategory)}")
        appendLine("control_error=${clean(status.controlError)}")
    }

    private fun clean(value: String?): String = value
        ?.lowercase()
        ?.replace(Regex("[^a-z0-9()._-]"), "_")
        ?: "none"
}
