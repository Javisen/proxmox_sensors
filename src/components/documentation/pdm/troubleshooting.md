PDM problems are easier to diagnose when connection, authentication, permissions and temporary data availability are considered separately.

### The PDM connection cannot be created

Verify:

- the hostname or IPv4 address, without `https://` or a port;
- connectivity from Home Assistant to PDM port 8443;
- the complete user and realm;
- Token ID and Token Secret;
- the SSL verification setting and certificate trust.

### Authentication works but some sensors are unavailable

Initial setup requires remote inventory and aggregate status, while resources, subscriptions, version and updates are separate data areas. A token can therefore connect but still lack access to some information.

Check the token permissions for the missing area. The exact least-privilege ACL recipe remains pending documentation.

### A remote or value looks stale

Temporary endpoint failures retain last-known-good information. Check the freshness attributes before interpreting retained data as current.

For updates, distinguish endpoint freshness from the age of the PDM snapshot. A successful HTTP poll does not mean PDM has refreshed every managed node at that moment.

### A remote disappeared from PDM

The integration removes a remote's entities and owned child device only after a fresh remote inventory proves that it is absent. API errors or ambiguous data do not authorize cleanup.

### Check Home Assistant logs

Open **Settings → System → Logs** and inspect entries from **Proxmox Extended Sensors** around the failed poll or setup attempt.

Remove credentials, token secrets, server addresses and other sensitive data before sharing logs publicly.
