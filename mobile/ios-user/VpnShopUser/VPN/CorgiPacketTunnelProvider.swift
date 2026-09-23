import NetworkExtension

/// Production Network Extension integration point.
/// A real provider must be provisioned with the app's signed tunnel profile
/// and the selected tunnel engine. It does not inspect private payloads.
final class CorgiPacketTunnelProvider: NEPacketTunnelProvider {
    override func startTunnel(options: [String : NSObject]?, completionHandler: @escaping (Error?) -> Void) {
        let settings = NEPacketTunnelNetworkSettings(tunnelRemoteAddress: "127.0.0.1")
        settings.ipv4Settings = NEIPv4Settings(addresses: ["10.77.0.2"], subnetMasks: ["255.255.255.0"])
        settings.ipv4Settings?.includedRoutes = [NEIPv4Route.default()]
        settings.dnsSettings = NEDNSSettings(servers: ["1.1.1.1", "9.9.9.9"])
        setTunnelNetworkSettings(settings) { error in completionHandler(error) }
    }
    override func stopTunnel(with reason: NEProviderStopReason, completionHandler: @escaping () -> Void) { completionHandler() }
}
