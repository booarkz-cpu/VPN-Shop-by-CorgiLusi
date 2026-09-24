package shop.remnawave.user.vpn

import android.content.Intent
import android.net.VpnService
/** A reserved integration point. No packet forwarding engine is bundled. */
class CorgiVpnService : VpnService() {
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Establishing a default route without forwarding packets would cut off traffic.
        stopSelf(startId)
        return START_NOT_STICKY
    }

    companion object {
        const val ACTION_START = "shop.corgi.vpn.START"
        const val ACTION_STOP = "shop.corgi.vpn.STOP"
    }
}
