Add PDM as its own Proxmox Extended Sensors configuration entry in Home Assistant.

Open:

**Settings → Devices & services → Add Integration**

Search for **Proxmox Extended Sensors**, enter the PDM server address and select **Proxmox Datacenter Manager** as the server type.

### Server address

Enter a hostname or IPv4 address without a protocol, path or port. The integration uses the PDM HTTPS API on port **8443** automatically.

IPv6 addresses are not currently accepted for PDM connections.

### Credentials

The PDM flow goes directly to API Token credentials. Enter:

- **User** — including its realm;
- **Token ID**;
- **Token Secret**;
- **Verify SSL Certificate** — according to the certificate trusted by Home Assistant.

The connection must provide the remote inventory and Datacenter status required for initial setup. Access to version, detailed resources, subscriptions and updates is checked separately, so restricted permissions can leave some information unavailable without changing the connection into a different server type.

After setup, the integration creates the PDM root device and discovers its configured remotes dynamically.
