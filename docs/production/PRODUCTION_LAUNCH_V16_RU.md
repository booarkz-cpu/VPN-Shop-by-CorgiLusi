# VPN Shop by Corgi Lusi v16 — Production Launch

## Архитектура
- Corgi Identity
- Corgi Edge
- WireGuard data plane
- FastAPI control plane
- Android VpnService / iOS Network Extension
- Admin Operations
- Billing/SSO integrations
- OpenTelemetry-ready observability

## Security gates
- signed tunnel profile
- explicit Lusi permissions
- private traffic payloads are not accepted by control-plane APIs
- secrets supplied only by environment/secret manager
- canary/rollback required for production release

## Release sequence
1. Provision Edge node.
2. Register node and verify heartbeat.
3. Run synthetic connectivity tests.
4. Canary one region.
5. Verify SLOs.
6. Expand traffic gradually.
7. Keep rollback available.

## External prerequisites
Native mobile entitlements, store signing, real payment/SSO credentials and cloud-managed HA are release-environment responsibilities.
