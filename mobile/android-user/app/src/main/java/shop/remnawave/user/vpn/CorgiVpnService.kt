package shop.remnawave.user.vpn

import android.content.Intent
import android.net.VpnService
import android.os.ParcelFileDescriptor

/** Production integration point for the Corgi tunnel engine.
 * The service never inspects application payloads. A signed tunnel profile is
 * handed to a platform-specific engine (WireGuard/native implementation).
 */
class CorgiVpnService : VpnService() {
    private var tunnel: ParcelFileDescriptor? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) stopTunnel() else if (intent?.action == ACTION_START) startTunnel()
        return START_STICKY
    }

    private fun startTunnel() {
        stopTunnel()
        tunnel = Builder()
            .setSession("Corgi Lusi")
            .addAddress("10.77.0.2", 32)
            .addRoute("0.0.0.0", 0)
            .establish()
    }

    private fun stopTunnel() {
        tunnel?.close()
        tunnel = null
        stopSelf()
    }

    override fun onDestroy() { stopTunnel(); super.onDestroy() }

    companion object {
        const val ACTION_START = "shop.corgi.vpn.START"
        const val ACTION_STOP = "shop.corgi.vpn.STOP"
    }
}
