package io.github.vel71184.teather.network

import android.net.Network
import io.github.vel71184.teather.relay.OutboundConnector
import io.github.vel71184.teather.relay.SocksDestination
import java.io.IOException
import java.net.Inet4Address
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Socket
import java.net.UnknownHostException

class AndroidNetworkConnector(
    private val networks: NetworkSelector,
    private val onSelected: (String) -> Unit,
) : OutboundConnector {

    override fun connect(destination: SocksDestination, timeoutMs: Int): Socket {
        val selected = networks.select()
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
}
