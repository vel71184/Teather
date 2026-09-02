package io.github.vel71184.teather.relay

import java.io.EOFException
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.net.Inet4Address
import java.net.Inet6Address
import java.net.InetAddress
import java.net.InetSocketAddress
import java.security.MessageDigest

data class SocksDestination(
    val host: String? = null,
    val address: InetAddress? = null,
    val port: Int,
) {
    init {
        require((host == null) xor (address == null)) { "Exactly one destination form is required" }
        require(port in 1..65535) { "Destination port is out of range" }
    }
}

class SocksProtocolException(
    val replyCode: Int,
    val replyAllowed: Boolean,
    message: String,
) : IOException(message)

object Socks5Protocol {
    const val REPLY_SUCCEEDED = 0x00
    const val REPLY_GENERAL_FAILURE = 0x01
    const val REPLY_NETWORK_UNREACHABLE = 0x03
    const val REPLY_HOST_UNREACHABLE = 0x04
    const val REPLY_CONNECTION_REFUSED = 0x05
    const val REPLY_TTL_EXPIRED = 0x06
    const val REPLY_COMMAND_NOT_SUPPORTED = 0x07
    const val REPLY_ADDRESS_TYPE_NOT_SUPPORTED = 0x08

    private const val VERSION = 0x05
    private const val METHOD_NO_AUTHENTICATION = 0x00
    private const val METHOD_USERNAME_PASSWORD = 0x02
    private const val METHOD_NOT_ACCEPTABLE = 0xff
    // RFC 1929 username/password sub-negotiation.
    private const val AUTH_VERSION = 0x01
    private const val AUTH_SUCCESS = 0x00
    private const val AUTH_FAILURE = 0x01
    private const val COMMAND_CONNECT = 0x01
    private const val ADDRESS_IPV4 = 0x01
    private const val ADDRESS_DOMAIN = 0x03
    private const val ADDRESS_IPV6 = 0x04

    /**
     * Method negotiation (RFC 1928) and, when [secret] is non-null, the
     * username/password sub-negotiation (RFC 1929).
     *
     * The relay listens on the phone's loopback, which every app on the device
     * can reach regardless of its permissions. When a [secret] is configured the
     * desktop client must present it as the SOCKS password; the value is only
     * learnable by a DUMP-privileged reader (adb / teatherd) from the relay's
     * status. A null [secret] keeps the no-auth path and is used only by tests.
     */
    fun negotiate(input: InputStream, output: OutputStream, secret: String? = null) {
        val version = input.readRequired()
        if (version != VERSION) {
            throw SocksProtocolException(REPLY_GENERAL_FAILURE, false, "Unsupported SOCKS version")
        }

        val methodCount = input.readRequired()
        if (methodCount == 0) {
            writeMethodChoice(output, METHOD_NOT_ACCEPTABLE)
            throw SocksProtocolException(REPLY_GENERAL_FAILURE, false, "Client supplied no methods")
        }
        val methods = input.readExactly(methodCount).mapTo(HashSet<Int>()) { it.toInt() and 0xff }

        if (secret == null) {
            if (METHOD_NO_AUTHENTICATION !in methods) {
                writeMethodChoice(output, METHOD_NOT_ACCEPTABLE)
                throw SocksProtocolException(REPLY_GENERAL_FAILURE, false, "No supported authentication method")
            }
            writeMethodChoice(output, METHOD_NO_AUTHENTICATION)
            return
        }

        if (METHOD_USERNAME_PASSWORD !in methods) {
            writeMethodChoice(output, METHOD_NOT_ACCEPTABLE)
            throw SocksProtocolException(REPLY_GENERAL_FAILURE, false, "Client cannot authenticate to the relay")
        }
        writeMethodChoice(output, METHOD_USERNAME_PASSWORD)
        authenticate(input, output, secret)
    }

    private fun writeMethodChoice(output: OutputStream, method: Int) {
        output.write(byteArrayOf(VERSION.toByte(), method.toByte()))
        output.flush()
    }

    private fun authenticate(input: InputStream, output: OutputStream, secret: String) {
        if (input.readRequired() != AUTH_VERSION) {
            throw SocksProtocolException(REPLY_GENERAL_FAILURE, false, "Unsupported authentication version")
        }
        input.readExactly(input.readRequired()) // username: unused, the secret is the whole credential
        val password = input.readExactly(input.readRequired())
        val accepted = MessageDigest.isEqual(password, secret.toByteArray(Charsets.US_ASCII))
        output.write(byteArrayOf(AUTH_VERSION.toByte(), (if (accepted) AUTH_SUCCESS else AUTH_FAILURE).toByte()))
        output.flush()
        if (!accepted) {
            throw SocksProtocolException(REPLY_GENERAL_FAILURE, false, "Relay authentication failed")
        }
    }

    fun readConnectRequest(input: InputStream): SocksDestination {
        if (input.readRequired() != VERSION) {
            throw SocksProtocolException(REPLY_GENERAL_FAILURE, false, "Invalid request version")
        }

        val command = input.readRequired()
        if (input.readRequired() != 0x00) {
            throw SocksProtocolException(REPLY_GENERAL_FAILURE, true, "Invalid reserved byte")
        }

        if (command != COMMAND_CONNECT) {
            throw SocksProtocolException(
                REPLY_COMMAND_NOT_SUPPORTED,
                true,
                "Only the CONNECT command is supported",
            )
        }

        val addressType = input.readRequired()
        val host: String?
        val address: InetAddress?
        when (addressType) {
            ADDRESS_IPV4 -> {
                host = null
                address = InetAddress.getByAddress(input.readExactly(4))
            }

            ADDRESS_DOMAIN -> {
                val length = input.readRequired()
                if (length == 0) {
                    throw SocksProtocolException(REPLY_HOST_UNREACHABLE, true, "Empty domain name")
                }
                val rawHost = String(input.readExactly(length), Charsets.US_ASCII)
                if (rawHost.any { it.code < 0x21 || it.code > 0x7e }) {
                    throw SocksProtocolException(REPLY_HOST_UNREACHABLE, true, "Invalid domain name")
                }
                host = rawHost
                address = null
            }

            ADDRESS_IPV6 -> {
                host = null
                address = InetAddress.getByAddress(input.readExactly(16))
            }

            else -> throw SocksProtocolException(
                REPLY_ADDRESS_TYPE_NOT_SUPPORTED,
                true,
                "Unsupported address type",
            )
        }

        val port = (input.readRequired() shl 8) or input.readRequired()
        if (port == 0) {
            throw SocksProtocolException(REPLY_GENERAL_FAILURE, true, "Port zero is invalid")
        }
        return SocksDestination(host = host, address = address, port = port)
    }

    fun writeReply(output: OutputStream, replyCode: Int, boundAddress: InetSocketAddress? = null) {
        val address = boundAddress?.address
        val addressBytes: ByteArray
        val addressType: Int
        when (address) {
            is Inet6Address -> {
                addressType = ADDRESS_IPV6
                addressBytes = address.address
            }

            is Inet4Address -> {
                addressType = ADDRESS_IPV4
                addressBytes = address.address
            }

            else -> {
                addressType = ADDRESS_IPV4
                addressBytes = byteArrayOf(0, 0, 0, 0)
            }
        }
        val port = boundAddress?.port?.coerceIn(0, 65535) ?: 0

        output.write(VERSION)
        output.write(replyCode)
        output.write(0x00)
        output.write(addressType)
        output.write(addressBytes)
        output.write((port ushr 8) and 0xff)
        output.write(port and 0xff)
        output.flush()
    }

    private fun InputStream.readRequired(): Int {
        val value = read()
        if (value < 0) throw EOFException("Unexpected end of SOCKS message")
        return value
    }

    private fun InputStream.readExactly(length: Int): ByteArray {
        val result = ByteArray(length)
        var offset = 0
        while (offset < result.size) {
            val count = read(result, offset, result.size - offset)
            if (count < 0) throw EOFException("Unexpected end of SOCKS message")
            offset += count
        }
        return result
    }
}
