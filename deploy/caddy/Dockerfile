ARG CADDY_BASE_IMAGE=caddy:2.10-alpine@sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d
FROM ${CADDY_BASE_IMAGE}
# The upstream executable has CAP_NET_BIND_SERVICE. With cap_drop: ALL this
# file capability makes exec fail with EPERM. Ports are enabled by the
# container's ip_unprivileged_port_start sysctl; no capability is needed.
RUN apk add --no-cache libcap && setcap -r /usr/bin/caddy
USER 10001:10001
