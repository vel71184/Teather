package io.github.vel71184.teather.service

import io.github.vel71184.teather.network.UpstreamPreference
import io.github.vel71184.teather.relay.RelayStatsSnapshot
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RelayStatusWireTest {
    @Test
    fun serializesVersionedStatusWithoutDestinationFields() {
        val status = RelayStatus(
            lifecycle = RelayLifecycle.RUNNING,
            configuration = RelayConfiguration(1080, UpstreamPreference.CELLULAR),
            boundPort = 1080,
            stats = RelayStatsSnapshot(2, 1, 1, 1, 120, 240, "cellular (validated)", "timeout", 4),
            failureCategory = null,
            secret = "00112233445566778899aabbccddeeff",
        )

        val wire = RelayStatusWire.serialize(status, CellularStatus(true, true))

        assertTrue(wire.startsWith("teather.status.version=2\n"))
        assertTrue(wire.contains("teather.status.security=${RelayStatusWire.SECURITY_VERSION}\n"))
        assertTrue(wire.contains("teather.status.secret=00112233445566778899aabbccddeeff\n"))
        assertTrue(wire.contains("lifecycle=running\n"))
        assertTrue(wire.contains("selected_upstream=cellular_(validated)\n"))
        assertTrue(wire.contains("bytes_internet_to_client=240\n"))
        assertFalse(wire.contains("destination"))
        assertFalse(wire.contains("serial"))
        assertFalse(wire.contains("subscriber"))
        assertFalse(wire.contains("device_id"))
    }

    @Test
    fun secretLineReadsNoneWhenTheRelayIsStopped() {
        val status = RelayStatus(
            lifecycle = RelayLifecycle.STOPPED,
            configuration = null,
            boundPort = null,
            stats = null,
            failureCategory = null,
            secret = null,
        )

        val wire = RelayStatusWire.serialize(status, CellularStatus(false, false))

        assertTrue(wire.contains("teather.status.secret=none\n"))
    }

    @Test
    fun startPolicyAttachesOrRefusesWithoutRestarting() {
        val current = RelayConfiguration(1080, UpstreamPreference.CELLULAR)
        assertEquals(
            RelayStartDecision.ATTACH,
            RelayStartPolicy.decide(RelayLifecycle.RUNNING, current, current),
        )
        assertEquals(
            RelayStartDecision.REFUSE_MISMATCH,
            RelayStartPolicy.decide(
                RelayLifecycle.RUNNING,
                current,
                RelayConfiguration(1081, UpstreamPreference.CELLULAR),
            ),
        )
        assertEquals(
            RelayStartDecision.REFUSE_MISMATCH,
            RelayStartPolicy.decide(
                RelayLifecycle.RUNNING,
                current,
                RelayConfiguration(1080, UpstreamPreference.WIFI),
            ),
        )
        assertEquals(
            RelayStartDecision.START,
            RelayStartPolicy.decide(RelayLifecycle.STOPPED, null, current),
        )
    }
}
