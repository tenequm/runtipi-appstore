# Transmission (VPN gateway)

Transmission BitTorrent client whose traffic is forced through a **self-hosted WireGuard VPN gateway** instead of a commercial VPN. A `gluetun` container (custom WireGuard mode) holds the network namespace and Transmission shares it, so:

- **Kill-switch**: if the tunnel drops, gluetun's firewall blocks all egress - nothing leaks to your real IP.
- **Real open port**: inbound peer connections arrive on a port forwarded by the gateway and DNAT'd back over the tunnel, so Transmission is connectable (fast downloads + healthy seeding ratio).
- **Egress identity** is the gateway's IP, not your home IP.

## Architecture

```
peers <-> gateway:PEER_PORT  --(WireGuard)-->  gluetun (kill-switch)  <->  transmission
                (DNAT tcp+udp)                   netns holder
```

## Requirements

You need a VPS / edge server running a WireGuard endpoint that:

1. Listens on the configured endpoint port (UDP).
2. Has `net.ipv4.ip_forward=1`, MASQUERADEs the tunnel subnet out to the internet.
3. DNATs the BitTorrent peer port (TCP + UDP) to this client's tunnel address.
4. Opens the WireGuard port and the peer port in any cloud firewall.

## Install fields

- **WireGuard Private Key** - this client's key (the peer the gateway accepts).
- **WireGuard Server Public Key / Endpoint IP / Endpoint Port** - the gateway.
- **WireGuard Tunnel Address** - e.g. `10.78.0.2/32`.
- **BitTorrent Peer Port** - must match the gateway's DNAT and Transmission's `peer-port`.
- **Allowed LAN / Docker Subnets** - so the web UI and *arr apps can reach Transmission past the kill-switch.

## Notes

- Set Transmission's `peer-port` in `settings.json` to the same value as the peer port field.
- DHT / PEX / LPD are typically left disabled for private trackers.
