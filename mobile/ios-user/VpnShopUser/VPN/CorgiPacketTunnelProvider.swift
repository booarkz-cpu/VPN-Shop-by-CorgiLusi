import NetworkExtension

/// Reserved integration point. A forwarding engine and signed profile are required.
final class CorgiPacketTunnelProvider: NEPacketTunnelProvider {
    override func startTunnel(options: [String : NSObject]?, completionHandler: @escaping (Error?) -> Void) {
        // Never install a default route until a real packet-forwarding engine exists.
        completionHandler(NSError(domain: "CorgiTunnel", code: 1,
                                  userInfo: [NSLocalizedDescriptionKey: "VPN engine is not configured. Import the subscription into an external VPN client."]))
    }
    override func stopTunnel(with reason: NEProviderStopReason, completionHandler: @escaping () -> Void) { completionHandler() }
}
