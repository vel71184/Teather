package io.github.vel71184.teather.network

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import io.github.vel71184.teather.relay.OutboundConnector
import io.github.vel71184.teather.relay.SocksDestination
import java.io.IOException
import java.net.Inet4Address
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Socket
import java.net.UnknownHostException

class AndroidNetworkConnector(
    context: Context,
    preference: UpstreamPreference,
    private val onSelected: (String) -> Unit,
) : OutboundConnector {
    private val connectivityManager =
        context.applicationContext.getSystemService(ConnectivityManager::class.java)

    /**
     * The transport newly opened sockets bind to. Swappable so the upstream can
     * change on a running relay with no listener teardown: sockets already open
     * keep their transport, and the next [connect] picks up the new preference.
     */
    @Volatile
    private var preference: UpstreamPreference = preference

    fun rebind(preference: UpstreamPreference) {
        this.preference = preference
    }

    override fun connect(destination: SocksDestination, timeoutMs: Int): Socket {
        val selected = selectNetwork()
        onSelected(selected.label)

        val addresses = destination.address?.let(::listOf)
            ?: resolve(selected.network, destination.host!!)
        var lastError: IOException? = null

        for (address in addresses.sortedBy { if (it is Inet4Address) 0 else 1 }) {
            val socket = selected.network.socketFactory.createSocket()
            try {
                socket.tcpNoDelay = true
                socket.keepAlive = true
                socket.connect(InetSocketAddress(address, destination.port), timeoutMs)
                return socket
            } catch (error: IOException) {
                lastError = error
                try {
                    socket.close()
                } catch (_: IOException) {
                    // Preserve the original connection failure.
                }
            }
        }

        throw lastError ?: UnknownHostException("No address available on selected Android network")
    }

    private fun resolve(network: Network, host: String): List<InetAddress> {
        val addresses = network.getAllByName(host).toList()
        if (addresses.isEmpty()) throw UnknownHostException("Selected Android network returned no address")
        return addresses
    }

    @Suppress("DEPRECATION") // P0 enumerates existing networks; P3 will own callback-based link lifecycle.
    private fun selectNetwork(): SelectedNetwork {
        val active = connectivityManager.activeNetwork
        val candidates = connectivityManager.allNetworks.mapNotNull { network ->
            val capabilities = connectivityManager.getNetworkCapabilities(network) ?: return@mapNotNull null
            if (!capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)) {
                return@mapNotNull null
            }
            if (capabilities.hasTransport(NetworkCapabilities.TRANSPORT_VPN)) {
                return@mapNotNull null
            }
            if (!matchesPreference(capabilities)) return@mapNotNull null

            val validated = capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
            val score = (if (validated) 100 else 0) + (if (network == active) 10 else 0)
            NetworkCandidate(
                selected = SelectedNetwork(network, label(capabilities, validated)),
                score = score,
            )
        }

        return candidates.maxByOrNull(NetworkCandidate::score)?.selected
            ?: throw NoUsableNetworkException(preference)
    }

    private fun matchesPreference(capabilities: NetworkCapabilities): Boolean = when (preference) {
        UpstreamPreference.AUTO -> true
        UpstreamPreference.CELLULAR -> capabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)
        UpstreamPreference.WIFI -> capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)
        UpstreamPreference.ETHERNET -> capabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)
    }

    private fun label(capabilities: NetworkCapabilities, validated: Boolean): String {
        val transport = when {
            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> "cellular"
            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) -> "wifi"
            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET) -> "ethernet"
            else -> "other"
        }
        return if (validated) "$transport (validated)" else "$transport (unvalidated)"
    }

    private data class NetworkCandidate(val selected: SelectedNetwork, val score: Int)
    private data class SelectedNetwork(val network: Network, val label: String)
}

class NoUsableNetworkException(preference: UpstreamPreference) :
    IOException("No usable ${preference.wireName} Android upstream")
