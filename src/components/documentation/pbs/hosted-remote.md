Proxmox Extended Sensors connects through the standard PBS HTTPS API. The PBS server therefore does not need to be on the same local network as Home Assistant, provided its API endpoint is securely reachable.

The integration has been tested successfully with a Proxmox Backup Server hosted by **Tuxis**, including datastore monitoring and maintenance operations authorized for the account.

<figure class="pve-figure">
  <img src="../../images/documentation/pbs/pbs-tuxis.png" width="1081" height="898" loading="lazy" decoding="async" alt="A hosted Tuxis Proxmox Backup Server displayed in the Proxmox Extended Sensors dashboard." />
  <figcaption>Hosted PBS — a Tuxis datastore and its available maintenance information inside the dashboard.</figcaption>
</figure>

### Availability depends on the provider

The information and actions available depend on the permissions and API access offered by the provider. Datastore monitoring may work normally while server-level hardware metrics remain unavailable on a hosted or multi-tenant PBS.

### Token ID formats

A self-hosted PBS can use a short Token ID:

<pre class="pbs-auth-example"><code>User:     homeassistant@realm
Token ID: home
Token:    &lt;API token secret&gt;</code></pre>

A hosted provider may require the complete API token identifier. This is the tested Tuxis example:

<pre class="pbs-auth-example"><code>Host:     https://pbs005.tuxis.nl
User:     FL000XX_USUARIO@pbs
Token ID: FL000XX@pbs!home
Token:    &lt;API token secret&gt;</code></pre>

The integration applies this rule:

- If **Token ID** already contains `!`, it is used directly as the complete API token identifier.
- If a short Token ID is provided, the integration constructs the identifier as `User!Token ID`.

The complete identifier shown above is documented for Tuxis. Do not assume that every hosted PBS provider uses the same account syntax.
