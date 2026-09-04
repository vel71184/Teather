package io.github.vel71184.teather

import android.content.Context
import android.content.res.Configuration

/**
 * The user's appearance choice for the app UI. Persisted alongside the other
 * relay preferences. Applied by overriding the activity's base configuration
 * (see [MainActivity.attachBaseContext]) so it works on the full minSdk range
 * without pulling in AppCompat.
 */
enum class ThemePreference(val wireName: String) {
    SYSTEM("system"),
    LIGHT("light"),
    DARK("dark");

    companion object {
        private const val PREFERENCES_NAME = "teather_p0"
        private const val KEY = "theme"

        fun fromWireName(value: String?): ThemePreference =
            entries.firstOrNull { it.wireName == value } ?: SYSTEM

        fun read(context: Context): ThemePreference = fromWireName(
            context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE).getString(KEY, null),
        )

        fun write(context: Context, preference: ThemePreference) {
            context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)
                .edit().putString(KEY, preference.wireName).apply()
        }

        /**
         * The `uiMode` a base [Configuration] should carry for this preference.
         * SYSTEM leaves the night bits as the platform set them; LIGHT and DARK
         * force them. Pure so it is unit-testable without a device.
         */
        fun applyNightMode(preference: ThemePreference, currentUiMode: Int): Int {
            val withoutNight = currentUiMode and Configuration.UI_MODE_NIGHT_MASK.inv()
            val night = when (preference) {
                SYSTEM -> currentUiMode and Configuration.UI_MODE_NIGHT_MASK
                LIGHT -> Configuration.UI_MODE_NIGHT_NO
                DARK -> Configuration.UI_MODE_NIGHT_YES
            }
            return withoutNight or night
        }
    }
}
