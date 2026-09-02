APP_ID = "io.github.vel71184.teather"
SERVICE_COMPONENT = f"{APP_ID}/.service.RelayService"
ACTION_START = f"{APP_ID}.action.START"
ACTION_STOP = f"{APP_ID}.action.STOP"
ACTION_RECONFIGURE = f"{APP_ID}.action.RECONFIGURE"

# Sentinel destination for tun2proxy's --udpgw-server. tun2proxy tunnels the UDP
# gateway stream through the SOCKS proxy with this as the CONNECT target; the
# phone's Socks5Server recognises it and hands the stream to its UdpGatewayServer
# instead of dialing out. It is never placed in a routing table. Must match
# UdpGatewayServer.SENTINEL_HOST/PORT in the Android app.
UDPGW_SENTINEL = "240.0.0.1:1"
# 2: the Android relay requires SOCKS username/password auth (RFC 1929) and
# publishes its per-run secret in the status wire. A schema-1 relay has no
# secret and no auth, so the two must not be paired.
STATUS_SCHEMA = 2
RELAY_PORT = 1080

# The desktop package bundles the matching Android APK so the client can install
# or upgrade it on the phone (D-029) — the two halves share a status schema and
# must stay in lockstep. `Teather.apk.version` is a two-line sidecar written by
# build-deb.sh: versionCode, then versionName.
BUNDLED_APK = "/usr/lib/teather/Teather.apk"
BUNDLED_APK_VERSION = "/usr/lib/teather/Teather.apk.version"

BUS_NAME = "io.github.vel71184.Teather1"
OBJECT_PATH = "/io/github/vel71184/Teather1"
INTERFACE = "io.github.vel71184.Teather1.Manager"

INTERFACE_NAME = "teather0"
CONNECTION_ID = "teather0"
INTERFACE_ADDRESS = "192.0.2.1/32"
VIRTUAL_DNS_ROUTE = "198.18.0.0/15"
VIRTUAL_DNS_POOL = "198.18.0.0/16"
DNS_SENTINEL = "198.19.0.1"
# D-022: additive, non-exclusive DNS. A positive priority is worse than every
# ordinary connection (NetworkManager's default is 100), so the physical link's
# resolver stays first in resolv.conf while it is present and the Teather
# sentinel is only consulted once the physical resolver is gone. D-021 used the
# exclusive negative range (-32768), which made Teather DNS win even while Wi-Fi
# was healthy; that is the behaviour this constant deliberately reverses.
DNS_PRIORITY = 32050
ROUTE_METRIC = 32000
TUN_MODE_TUN = 1
