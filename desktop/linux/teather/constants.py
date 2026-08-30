APP_ID = "io.github.vel71184.teather"
SERVICE_COMPONENT = f"{APP_ID}/.service.RelayService"
ACTION_START = f"{APP_ID}.action.START"
ACTION_STOP = f"{APP_ID}.action.STOP"
STATUS_SCHEMA = 1
RELAY_PORT = 1080

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
