package io.github.vel71184.teather.network

/** The Android transport Teather should use for newly opened outbound sockets. */
enum class UpstreamPreference(val wireName: String) {
    AUTO("auto"),
    CELLULAR("cellular"),
    WIFI("wifi"),
    ETHERNET("ethernet");

    companion object {
        fun fromWireName(value: String?): UpstreamPreference =
            entries.firstOrNull { it.wireName == value } ?: CELLULAR
    }
}
