package io.github.vel71184.teather.relay

import java.io.EOFException
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.net.Inet6Address
import java.net.InetAddress
import java.net.InetSocketAddress

/**
 * The badvpn-style "udpgw" framing that `tun2proxy --udpgw-server` speaks over a
 * TCP stream to carry UDP datagrams. Teather's relay terminates it on the phone
 * so UDP crosses the TCP-only ADB link without a VpnService or a packet stack.
 *
 * ```
 * +-----+  +-------+---------+  +------+----------+----------+  +----------+
 * | LEN |  | FLAGS | CONN_ID |  | ATYP | DST.ADDR | DST.PORT |  |   DATA   |
 * +-----+  +-------+---------+  +------+----------+----------+  +----------+
 * |  2  |  |   1   |    2    |  |  1   | Variable |    2     |  | Variable |
 * ```
 *
 * LEN counts every byte after itself. The address block is present only when the
 * DATA flag is set. All integers are big-endian.
 */
object UdpGatewayProtocol {
    const val FLAG_KEEPALIVE = 0x01
    const val FLAG_DATA = 0x02
    const val FLAG_ERROR = 0x20

    private const val ATYP_IPV4 = 0x01
    private const val ATYP_DOMAIN = 0x03
    private const val ATYP_IPV6 = 0x04

    /** Upper bound on a single frame body — the most the 16-bit length field can express. */
    const val MAX_BODY = 0xffff

    sealed interface Target {
        data class Ip(val socketAddress: InetSocketAddress) : Target
        data class Domain(val host: String, val port: Int) : Target
    }

    data class Packet(
        val flags: Int,
        val connId: Int,
        val target: Target?,
        val data: ByteArray,
    ) {
        val isData: Boolean get() = flags and FLAG_DATA != 0
        val isKeepalive: Boolean get() = flags and FLAG_KEEPALIVE != 0

        override fun equals(other: Any?): Boolean =
            other is Packet && flags == other.flags && connId == other.connId &&
                target == other.target && data.contentEquals(other.data)

        override fun hashCode(): Int =
            (flags * 31 + connId) * 31 + data.contentHashCode()
    }

    fun keepalive(connId: Int) = Packet(FLAG_KEEPALIVE, connId, null, ByteArray(0))

    fun error(connId: Int) = Packet(FLAG_ERROR, connId, null, ByteArray(0))

    fun data(connId: Int, source: InetSocketAddress, payload: ByteArray) =
        Packet(FLAG_DATA, connId, Target.Ip(source), payload)

    /** Reads one frame, or throws [EOFException] at a clean end of stream. */
    fun read(input: InputStream): Packet {
        val length = ((input.readOrFail() shl 8) or input.readOrFail())
        if (length < 3 || length > MAX_BODY) {
            throw IOException("udpgw frame length $length out of range")
        }
        val body = ByteArray(length)
        var read = 0
        while (read < length) {
            val n = input.read(body, read, length - read)
            if (n < 0) throw EOFException("truncated udpgw frame")
            read += n
        }

        val flags = body[0].toInt() and 0xff
        val connId = ((body[1].toInt() and 0xff) shl 8) or (body[2].toInt() and 0xff)
        var offset = 3
        var target: Target? = null
        if (flags and FLAG_DATA != 0) {
            val (parsed, next) = readTarget(body, offset)
            target = parsed
            offset = next
        }
        val data = body.copyOfRange(offset, body.size)
        return Packet(flags, connId, target, data)
    }

    fun write(output: OutputStream, packet: Packet) {
        val addressLength = when {
            packet.flags and FLAG_DATA == 0 -> 0
            else -> when (val target = requireNotNull(packet.target) { "DATA frame needs a target" }) {
                is Target.Ip -> 1 + target.socketAddress.address.address.size + 2
                is Target.Domain -> 1 + 1 + target.host.toByteArray(Charsets.US_ASCII).size + 2
            }
        }
        val bodyLength = 3 + addressLength + packet.data.size
        require(bodyLength <= MAX_BODY) { "udpgw frame body $bodyLength exceeds $MAX_BODY" }

        val framed = ByteArray(2 + bodyLength)
        framed[0] = (bodyLength ushr 8).toByte()
        framed[1] = bodyLength.toByte()
        var offset = 2
        framed[offset++] = packet.flags.toByte()
        framed[offset++] = (packet.connId ushr 8).toByte()
        framed[offset++] = packet.connId.toByte()
        if (packet.flags and FLAG_DATA != 0) {
            offset = writeTarget(framed, offset, packet.target!!)
        }
        System.arraycopy(packet.data, 0, framed, offset, packet.data.size)

        synchronized(output) {
            output.write(framed)
            output.flush()
        }
    }

    private fun readTarget(body: ByteArray, start: Int): Pair<Target, Int> {
        var offset = start
        if (offset >= body.size) throw IOException("udpgw address truncated")
        val atyp = body[offset++].toInt() and 0xff
        return when (atyp) {
            ATYP_IPV4 -> {
                requireRemaining(body, offset, 4 + 2)
                val raw = body.copyOfRange(offset, offset + 4); offset += 4
                val port = readPort(body, offset); offset += 2
                Target.Ip(InetSocketAddress(InetAddress.getByAddress(raw), port)) to offset
            }
            ATYP_IPV6 -> {
                requireRemaining(body, offset, 16 + 2)
                val raw = body.copyOfRange(offset, offset + 16); offset += 16
                val port = readPort(body, offset); offset += 2
                Target.Ip(InetSocketAddress(InetAddress.getByAddress(raw), port)) to offset
            }
            ATYP_DOMAIN -> {
                if (offset >= body.size) throw IOException("udpgw address truncated")
                val len = body[offset++].toInt() and 0xff
                requireRemaining(body, offset, len + 2)
                val host = String(body, offset, len, Charsets.US_ASCII); offset += len
                val port = readPort(body, offset); offset += 2
                Target.Domain(host, port) to offset
            }
            else -> throw IOException("udpgw address type $atyp unsupported")
        }
    }

    private fun requireRemaining(body: ByteArray, offset: Int, needed: Int) {
        if (offset + needed > body.size) throw IOException("udpgw address truncated")
    }

    private fun writeTarget(body: ByteArray, start: Int, target: Target): Int {
        var offset = start
        when (target) {
            is Target.Ip -> {
                val address = target.socketAddress.address
                val raw = address.address
                body[offset++] = if (address is Inet6Address) ATYP_IPV6.toByte() else ATYP_IPV4.toByte()
                System.arraycopy(raw, 0, body, offset, raw.size); offset += raw.size
                offset = writePort(body, offset, target.socketAddress.port)
            }
            is Target.Domain -> {
                val name = target.host.toByteArray(Charsets.US_ASCII)
                body[offset++] = ATYP_DOMAIN.toByte()
                body[offset++] = name.size.toByte()
                System.arraycopy(name, 0, body, offset, name.size); offset += name.size
                offset = writePort(body, offset, target.port)
            }
        }
        return offset
    }

    private fun readPort(body: ByteArray, offset: Int): Int {
        if (offset + 2 > body.size) throw IOException("udpgw port truncated")
        return ((body[offset].toInt() and 0xff) shl 8) or (body[offset + 1].toInt() and 0xff)
    }

    private fun writePort(body: ByteArray, offset: Int, port: Int): Int {
        body[offset] = (port ushr 8).toByte()
        body[offset + 1] = port.toByte()
        return offset + 2
    }

    private fun InputStream.readOrFail(): Int {
        val value = read()
        if (value < 0) throw EOFException("end of udpgw stream")
        return value
    }
}
