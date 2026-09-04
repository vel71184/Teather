package io.github.vel71184.teather

import android.content.res.Configuration
import org.junit.Assert.assertEquals
import org.junit.Test

class ThemePreferenceTest {
    private val night = Configuration.UI_MODE_NIGHT_YES or Configuration.UI_MODE_TYPE_NORMAL
    private val day = Configuration.UI_MODE_NIGHT_NO or Configuration.UI_MODE_TYPE_NORMAL

    @Test
    fun unknownWireNamesFallBackToSystem() {
        assertEquals(ThemePreference.SYSTEM, ThemePreference.fromWireName(null))
        assertEquals(ThemePreference.SYSTEM, ThemePreference.fromWireName("sepia"))
        assertEquals(ThemePreference.DARK, ThemePreference.fromWireName("dark"))
    }

    @Test
    fun systemLeavesTheNightBitsUntouched() {
        assertEquals(night, ThemePreference.applyNightMode(ThemePreference.SYSTEM, night))
        assertEquals(day, ThemePreference.applyNightMode(ThemePreference.SYSTEM, day))
    }

    @Test
    fun lightAndDarkForceTheNightBitsAndKeepTheRest() {
        assertEquals(day, ThemePreference.applyNightMode(ThemePreference.LIGHT, night))
        assertEquals(night, ThemePreference.applyNightMode(ThemePreference.DARK, day))
        assertEquals(
            Configuration.UI_MODE_TYPE_NORMAL,
            ThemePreference.applyNightMode(ThemePreference.LIGHT, day) and Configuration.UI_MODE_TYPE_MASK,
        )
    }
}
