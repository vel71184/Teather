package io.github.vel71184.teather.network

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import java.io.IOException

/**
 * Picks which Android transport Teather's outbound traffic uses, shared by the
 * TCP [AndroidNetworkConnector] and the UDP gateway so both bind to the same
 * link.
 *
 * The preference is swappable: changing it takes effect on the next [select],
 * so a running relay can move to another transport with no teardown — sockets
 * already open keep the link they were created on.
 */
class NetworkSelector(context: Context, preference: UpstreamPreference) {
    private val connectivityManager =
        context.applicationContext.getSystemService(ConnectivityManager::class.java)

    @Volatile
    private var preference: UpstreamPreference = preference

    fun rebind(preference: UpstreamPreference) {
        this.preference = preference
    }

    data class Selected(val network: Network, val label: String)

    @Suppress("DEPRECATION") // P0 enumerates existing networks; P3 will own callback-based link lifecycle.
    fun select(): Selected {
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
            Candidate(Selected(network, label(capabilities, validated)), score)
        }

        return candidates.maxByOrNull(Candidate::score)?.selected
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

    private data class Candidate(val selected: Selected, val score: Int)
}

class NoUsableNetworkException(preference: UpstreamPreference) :
    IOException("No usable ${preference.wireName} Android upstream")
