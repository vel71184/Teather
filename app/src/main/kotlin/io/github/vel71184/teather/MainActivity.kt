package io.github.vel71184.teather

import android.Manifest
import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.res.Configuration
import android.net.Uri
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import io.github.vel71184.teather.network.UpstreamPreference
import io.github.vel71184.teather.service.RelayConfiguration
import io.github.vel71184.teather.service.RelayLifecycle
import io.github.vel71184.teather.service.RelayRuntime
import io.github.vel71184.teather.service.RelayService
import io.github.vel71184.teather.service.RelayStatus
import io.github.vel71184.teather.service.RelayStatusWire
import java.util.Locale

class MainActivity : Activity() {
    private val handler = Handler(Looper.getMainLooper())
    private lateinit var upstreamSpinner: Spinner
    private lateinit var themeSpinner: Spinner
    private lateinit var portInput: EditText
    private lateinit var statusText: TextView

    private val statusUpdater = object : Runnable {
        override fun run() {
            renderStatus(RelayRuntime.snapshot())
            handler.postDelayed(this, STATUS_REFRESH_MS)
        }
    }

    /**
     * Honour the saved [ThemePreference] without AppCompat: hand the activity a
     * base context whose Configuration forces the night-mode bits, so the
     * `-night` resources resolve to the user's choice. [recreate] re-runs this.
     */
    override fun attachBaseContext(newBase: Context) {
        val current = newBase.resources.configuration
        val overridden = Configuration(current).apply {
            uiMode = ThemePreference.applyNightMode(ThemePreference.read(newBase), current.uiMode)
        }
        super.attachBaseContext(newBase.createConfigurationContext(overridden))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(buildContent())
        restoreConfiguration()
        installUpstreamListener()
        installThemeListener()
    }

    /**
     * Let the upstream picker take effect on a running relay without a
     * stop/start: send ACTION_RECONFIGURE, which rebinds the relay's upstream
     * live. Installed after [restoreConfiguration] so restoring the saved choice
     * does not fire it, and it only acts when the choice actually differs from
     * what the relay is on.
     */
    private fun installUpstreamListener() {
        upstreamSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                val upstream = UpstreamPreference.entries[position]
                preferences.edit().putString(PREFERENCE_UPSTREAM, upstream.wireName).apply()

                val status = RelayRuntime.snapshot()
                if (status.lifecycle != RelayLifecycle.RUNNING) return
                if (status.configuration?.upstream == upstream) return

                val port = portInput.text.toString().toIntOrNull()
                    ?: status.configuration?.port
                    ?: RelayConfiguration.DEFAULT_PORT
                startForegroundService(
                    Intent(this@MainActivity, RelayService::class.java)
                        .setAction(RelayService.ACTION_RECONFIGURE)
                        .putExtra(RelayService.EXTRA_PORT, port)
                        .putExtra(RelayService.EXTRA_UPSTREAM, upstream.wireName),
                )
                Toast.makeText(
                    this@MainActivity,
                    getString(R.string.upstream_switched, upstreamDisplayName(upstream)),
                    Toast.LENGTH_SHORT,
                ).show()
            }

            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
        }
    }

    /**
     * Attached after [restoreConfiguration] so setting the saved selection does
     * not fire it. A real change is persisted and the activity recreated so
     * [attachBaseContext] re-applies with the new choice.
     */
    private fun installThemeListener() {
        themeSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                val choice = ThemePreference.entries[position]
                if (choice == ThemePreference.read(this@MainActivity)) return
                ThemePreference.write(this@MainActivity, choice)
                recreate()
            }

            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
        }
    }

    override fun onResume() {
        super.onResume()
        requestNotificationPermissionIfNeeded()
        handler.post(statusUpdater)
    }

    override fun onPause() {
        handler.removeCallbacks(statusUpdater)
        super.onPause()
    }

    private fun buildContent(): ScrollView {
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(24), dp(20), dp(32))
        }

        content.addView(TextView(this).apply {
            text = getString(R.string.screen_title)
            textSize = 28f
            typeface = Typeface.DEFAULT_BOLD
        })
        content.addView(TextView(this).apply {
            text = getString(R.string.screen_description)
            textSize = 16f
            setPadding(0, dp(10), 0, dp(22))
        })

        content.addView(fieldLabel(R.string.upstream_label))
        upstreamSpinner = Spinner(this).apply {
            adapter = ArrayAdapter(
                this@MainActivity,
                android.R.layout.simple_spinner_dropdown_item,
                UpstreamPreference.entries.map(::upstreamDisplayName),
            )
        }
        content.addView(
            upstreamSpinner,
            LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT),
        )

        content.addView(fieldLabel(R.string.port_label).apply { setPadding(0, dp(18), 0, dp(6)) })
        portInput = EditText(this).apply {
            inputType = InputType.TYPE_CLASS_NUMBER
            setText(RelayConfiguration.DEFAULT_PORT.toString())
            contentDescription = getString(R.string.port_label)
        }
        content.addView(
            portInput,
            LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT),
        )

        val primaryActions = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(0, dp(20), 0, 0)
        }
        primaryActions.addView(Button(this).apply {
            text = getString(R.string.start_relay)
            setOnClickListener { startRelay() }
        }, weightedButtonParams())
        primaryActions.addView(Button(this).apply {
            text = getString(R.string.stop_relay)
            setOnClickListener { stopRelay() }
        }, weightedButtonParams().apply { marginStart = dp(10) })
        content.addView(primaryActions)

        content.addView(Button(this).apply {
            text = getString(R.string.copy_commands)
            setOnClickListener { copyLaptopCommands() }
        }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            topMargin = dp(10)
        })

        content.addView(Button(this).apply {
            text = getString(R.string.get_desktop_client)
            setOnClickListener { openDownloadPage() }
        }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            topMargin = dp(10)
        })

        content.addView(fieldLabel(R.string.theme_label).apply { setPadding(0, dp(24), 0, dp(6)) })
        themeSpinner = Spinner(this).apply {
            adapter = ArrayAdapter(
                this@MainActivity,
                android.R.layout.simple_spinner_dropdown_item,
                ThemePreference.entries.map(::themeDisplayName),
            )
        }
        content.addView(
            themeSpinner,
            LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT),
        )

        content.addView(fieldLabel(R.string.status_label).apply { setPadding(0, dp(24), 0, dp(8)) })
        statusText = TextView(this).apply {
            text = getString(R.string.status_stopped)
            textSize = 14f
            typeface = Typeface.MONOSPACE
            setTextIsSelectable(true)
            setPadding(dp(14), dp(14), dp(14), dp(14))
            setBackgroundColor(resources.getColor(R.color.status_background, theme))
        }
        content.addView(
            statusText,
            LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT),
        )

        return ScrollView(this).apply {
            addView(
                content,
                ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT),
            )
        }
    }

    private fun startRelay() {
        val port = portInput.text.toString().toIntOrNull()
        if (port == null || port !in 1024..65535) {
            Toast.makeText(this, R.string.invalid_port, Toast.LENGTH_LONG).show()
            return
        }
        val upstream = UpstreamPreference.entries[upstreamSpinner.selectedItemPosition]
        preferences.edit()
            .putInt(PREFERENCE_PORT, port)
            .putString(PREFERENCE_UPSTREAM, upstream.wireName)
            .apply()

        val intent = Intent(this, RelayService::class.java)
            .setAction(RelayService.ACTION_START)
            .putExtra(RelayService.EXTRA_PORT, port)
            .putExtra(RelayService.EXTRA_UPSTREAM, upstream.wireName)
        startForegroundService(intent)
    }

    private fun stopRelay() {
        stopService(Intent(this, RelayService::class.java))
        RelayRuntime.stop()
        renderStatus(RelayRuntime.snapshot())
    }

    private fun copyLaptopCommands() {
        val port = portInput.text.toString().toIntOrNull() ?: RelayConfiguration.DEFAULT_PORT
        val commands = """
            adb forward tcp:$port tcp:$port
            curl --fail --show-error --socks5-hostname 127.0.0.1:$port https://example.com/
        """.trimIndent()
        val clipboard = getSystemService(ClipboardManager::class.java)
        clipboard.setPrimaryClip(ClipData.newPlainText("Teather relay commands", commands))
        Toast.makeText(this, R.string.commands_copied, Toast.LENGTH_SHORT).show()
    }

    /**
     * The client for the desktop is not bundled here — it is per-distro and
     * carries a compiled tunnel binary. Send the user to the project's releases
     * page to pick the build for whatever machine they want to relay from.
     */
    private fun openDownloadPage() {
        try {
            startActivity(
                Intent(Intent.ACTION_VIEW, Uri.parse(getString(R.string.download_url)))
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
            )
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, R.string.no_browser, Toast.LENGTH_LONG).show()
        }
    }

    private fun restoreConfiguration() {
        val port = preferences.getInt(PREFERENCE_PORT, RelayConfiguration.DEFAULT_PORT)
        val upstream = UpstreamPreference.fromWireName(
            preferences.getString(PREFERENCE_UPSTREAM, UpstreamPreference.CELLULAR.wireName),
        )
        portInput.setText(port.toString())
        upstreamSpinner.setSelection(UpstreamPreference.entries.indexOf(upstream))
        themeSpinner.setSelection(ThemePreference.entries.indexOf(ThemePreference.read(this)))
    }

    private fun renderStatus(status: RelayStatus) {
        val snapshot = status.stats
        statusText.text = buildString {
            append("State: ").append(status.lifecycle.name.lowercase(Locale.US)).append('\n')
            append("Security level: ").append(RelayStatusWire.SECURITY_VERSION).append('\n')
            status.configuration?.let { configuration ->
                append("Listener: 127.0.0.1:").append(status.boundPort ?: configuration.port).append('\n')
                append("Requested upstream: ").append(configuration.upstream.wireName).append('\n')
            }
            if (status.lifecycle == RelayLifecycle.FAILED) {
                append("Failure: ").append(status.failureCategory ?: "unknown").append('\n')
            }
            snapshot?.let {
                append("Selected upstream: ").append(it.lastUpstream ?: "not used yet").append('\n')
                append("Active sessions: ").append(it.activeSessions).append('\n')
                append("Established: ").append(it.establishedSessions).append('\n')
                append("Accepted / rejected: ").append(it.acceptedClients).append(" / ").append(it.rejectedClients).append('\n')
                append("Client → Internet: ").append(formatBytes(it.bytesClientToInternet)).append('\n')
                append("Internet → Client: ").append(formatBytes(it.bytesInternetToClient)).append('\n')
                append("Last error category: ").append(it.lastErrorCategory ?: "none")
            }
        }
    }

    private fun formatBytes(bytes: Long): String = when {
        bytes < 1024 -> "$bytes B"
        bytes < 1024 * 1024 -> String.format(Locale.US, "%.1f KiB", bytes / 1024.0)
        else -> String.format(Locale.US, "%.1f MiB", bytes / (1024.0 * 1024.0))
    }

    private fun upstreamDisplayName(preference: UpstreamPreference): String = getString(
        when (preference) {
            UpstreamPreference.AUTO -> R.string.upstream_auto
            UpstreamPreference.CELLULAR -> R.string.upstream_cellular
            UpstreamPreference.WIFI -> R.string.upstream_wifi
            UpstreamPreference.ETHERNET -> R.string.upstream_ethernet
        },
    )

    private fun themeDisplayName(preference: ThemePreference): String = getString(
        when (preference) {
            ThemePreference.SYSTEM -> R.string.theme_system
            ThemePreference.LIGHT -> R.string.theme_light
            ThemePreference.DARK -> R.string.theme_dark
        },
    )

    private fun fieldLabel(resourceId: Int): TextView = TextView(this).apply {
        text = getString(resourceId)
        textSize = 15f
        typeface = Typeface.DEFAULT_BOLD
        setPadding(0, 0, 0, dp(6))
    }

    private fun weightedButtonParams() = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)

    private fun requestNotificationPermissionIfNeeded() {
        if (
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), NOTIFICATION_PERMISSION_REQUEST)
        }
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private val preferences
        get() = getSharedPreferences(PREFERENCES_NAME, MODE_PRIVATE)

    companion object {
        private const val STATUS_REFRESH_MS = 1_000L
        private const val NOTIFICATION_PERMISSION_REQUEST = 41
        private const val PREFERENCES_NAME = "teather_p0"
        private const val PREFERENCE_PORT = "port"
        private const val PREFERENCE_UPSTREAM = "upstream"
    }
}
