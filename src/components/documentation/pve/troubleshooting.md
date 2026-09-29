Most PVE monitoring problems can be narrowed down by identifying where the information stops being available: the connection to Proxmox, authentication and permissions, the Proxmox API, or the additional hardware information provided by the host.

Start with the simplest checks before changing the integration configuration.

### The integration cannot connect to PVE

If the initial connection fails, verify the basic connection information first:

- confirm that the PVE host address is correct;
- confirm that Home Assistant can reach the Proxmox server over the network;
- verify the configured Proxmox user;
- verify the Token ID and Token Secret when API Token authentication is used;
- check whether SSL certificate verification matches your environment.

Remember that **User**, **Token ID** and **Token Secret** are separate values in the configuration flow.

If you recently recreated an API Token, make sure Home Assistant is using the new secret.

### Authentication works, but some information is missing

A successful login does not necessarily mean that the account can access every endpoint used by the integration.

If the PVE connection succeeds but particular information or functionality is unavailable, check the permissions assigned to the dedicated Home Assistant user and API Token.

Pay particular attention to **Privilege Separation** when API Token authentication is used.

A token can authenticate correctly while still lacking permission to access some Proxmox information or perform supported actions.

### A VM or CT does not appear

Proxmox Extended Sensors only needs to expose the guests that you have chosen to monitor.

If a VM or container is missing, first confirm that it is included in the integration configuration.

Also verify that the guest still exists in Proxmox and that the configured account can access its information.

In a cluster, a guest may move between nodes. V5 is designed to follow monitored guests across nodes within the configured cluster, so a normal migration should not require the Home Assistant configuration to be recreated.

### A sensor is unavailable or has no value

An unavailable entity does not always mean that the integration itself has failed.

The underlying information may temporarily be unavailable from Proxmox, the node may be unreachable, the guest may be stopped, or the corresponding information may not be provided in the current state.

Check related entities before diagnosing an individual sensor in isolation.

For example, if several entities belonging to the same node become unavailable simultaneously, check the node connection before investigating each sensor separately.

### Hardware sensors are missing

Hardware monitoring depends on what the PVE host can detect.

If CPU, chipset, NVMe, SMART, DIMM or other hardware information is missing, first verify that the information is actually available on the Proxmox host.

Different machines can expose very different sets of hardware sensors.

The absence of a particular sensor is therefore not automatically an integration error.

Storage controllers, drivers, passthrough configurations and hardware support can also affect what information is available.

### Storage information looks incomplete

Remember that **PVE Storage**, **Mounted Disks** and **physical drive monitoring** represent different views of storage.

A storage resource configured in Proxmox does not necessarily correspond directly to a physical disk detected by hardware monitoring.

Likewise, a mounted disk may be available to the host without being represented as the same type of PVE storage resource.

Check which type of information you expect before assuming that a storage entity is missing.

### Controls do not work

If monitoring works but an action such as starting, stopping, shutting down or rebooting a guest fails, check the permissions assigned to the Proxmox account and API Token.

Read access can be sufficient for monitoring while control operations require additional privileges.

Also verify that the requested action is valid for the current state of the VM or container.

### Check Home Assistant logs

When the cause is not obvious, Home Assistant logs can provide additional information about connection failures, permission errors or data that could not be retrieved.

Open:

**Settings → System → Logs**

Look for entries related to **Proxmox Extended Sensors** around the time the problem occurred.

When reporting a problem, include the relevant error information but remove credentials, API Token secrets and any other sensitive information before sharing logs publicly.

### Before opening an issue

Before reporting a problem, try to determine whether it affects:

- the complete PVE connection;
- one particular node;
- a VM or container;
- storage information;
- hardware monitoring;
- or a specific control or entity.

A focused description makes troubleshooting much easier.

Include the relevant Proxmox Extended Sensors version, Home Assistant version and Proxmox VE version together with the error or unexpected behaviour.

Never include passwords or API Token secrets.
