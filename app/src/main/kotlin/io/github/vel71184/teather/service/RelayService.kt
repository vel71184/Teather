package io.github.vel71184.teather.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.util.Log
import io.github.vel71184.teather.MainActivity
import io.github.vel71184.teather.R
import io.github.vel71184.teather.network.UpstreamPreference
import java.io.FileDescriptor
import java.io.PrintWriter

class RelayService : Service() {
    private var preserveFailureOnDestroy = false

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopRelayAndSelf()
            return START_NOT_STICKY
        }

        if (intent?.action != ACTION_START) {
            Log.w(LOG_TAG, "relay.lifecycle.unsupported-action")
            return START_NOT_STICKY
        }

        startInForeground(startingNotification())
        val port = intent?.getIntExtra(EXTRA_PORT, RelayConfiguration.DEFAULT_PORT)
            ?: RelayConfiguration.DEFAULT_PORT
        val upstream = UpstreamPreference.fromWireName(intent?.getStringExtra(EXTRA_UPSTREAM))

        val configuration = try {
            RelayConfiguration(port = port, upstream = upstream)
        } catch (error: IllegalArgumentException) {
            Log.e(LOG_TAG, "relay.lifecycle.invalid-configuration", error)
            stopRelayAndSelf()
            return START_NOT_STICKY
        }

        val status = RelayRuntime.start(applicationContext, configuration)
        if (status.controlError != null) {
            Log.w(LOG_TAG, "relay.lifecycle.${status.controlError}")
        }
        if (status.lifecycle == RelayLifecycle.RUNNING) {
            notificationManager.notify(NOTIFICATION_ID, runningNotification(status))
        } else {
            stopServicePreservingFailure()
        }
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        if (!preserveFailureOnDestroy) RelayRuntime.stop()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun dump(fd: FileDescriptor, writer: PrintWriter, args: Array<out String>) {
        val status = RelayRuntime.snapshot()
        val cellular = AndroidRelayStatus.cellularStatus(applicationContext)
        writer.print(RelayStatusWire.serialize(status, cellular))
    }

    private fun startInForeground(notification: Notification) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE,
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun stopRelayAndSelf() {
        preserveFailureOnDestroy = false
        RelayRuntime.stop()
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun stopServicePreservingFailure() {
        preserveFailureOnDestroy = true
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            getString(R.string.notification_channel_name),
            NotificationManager.IMPORTANCE_LOW,
        ).apply {
            description = getString(R.string.notification_channel_description)
            setShowBadge(false)
        }
        notificationManager.createNotificationChannel(channel)
    }

    private fun startingNotification(): Notification = baseNotificationBuilder()
        .setContentText(getString(R.string.notification_starting))
        .build()

    private fun runningNotification(status: RelayStatus): Notification {
        val configuration = requireNotNull(status.configuration)
        return baseNotificationBuilder()
            .setContentText(
                getString(
                    R.string.notification_running,
                    requireNotNull(status.boundPort),
                    configuration.upstream.wireName,
                ),
            )
            .addAction(
                Notification.Action.Builder(
                    null,
                    getString(R.string.notification_stop),
                    stopPendingIntent(),
                ).build(),
            )
            .build()
    }

    private fun baseNotificationBuilder(): Notification.Builder = Notification.Builder(this, CHANNEL_ID)
        .setSmallIcon(R.drawable.ic_teather)
        .setContentTitle(getString(R.string.app_name))
        .setContentIntent(activityPendingIntent())
        .setOngoing(true)
        .setOnlyAlertOnce(true)
        .setCategory(Notification.CATEGORY_SERVICE)

    private fun activityPendingIntent(): PendingIntent = PendingIntent.getActivity(
        this,
        0,
        Intent(this, MainActivity::class.java),
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
    )

    private fun stopPendingIntent(): PendingIntent = PendingIntent.getService(
        this,
        1,
        Intent(this, RelayService::class.java).setAction(ACTION_STOP),
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
    )

    private val notificationManager: NotificationManager
        get() = getSystemService(NotificationManager::class.java)

    companion object {
        const val ACTION_START = "io.github.vel71184.teather.action.START"
        const val ACTION_STOP = "io.github.vel71184.teather.action.STOP"
        const val EXTRA_PORT = "relay_port"
        const val EXTRA_UPSTREAM = "relay_upstream"

        private const val CHANNEL_ID = "teather_relay"
        private const val NOTIFICATION_ID = 1001
        private const val LOG_TAG = "Teather"
    }
}
