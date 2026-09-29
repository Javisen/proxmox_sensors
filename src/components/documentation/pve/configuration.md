Once authentication has been prepared in Proxmox VE, the PVE connection can be added to Proxmox Extended Sensors from Home Assistant.

The configuration flow guides you through the connection details and the monitoring options available for the server.

### Add the integration

In Home Assistant, open:

**Settings → Devices & services → Add Integration**

Search for **Proxmox Extended Sensors** and start the configuration flow.

Select **Proxmox VE (PVE)** when choosing the type of server you want to configure.

### Connect to the PVE server

Enter the connection information for your Proxmox VE host.

The configuration flow will request the server address and the authentication information prepared in the previous section.

When API Token authentication is used, enter the Proxmox user, Token ID and Token Secret as separate values.

<figure class="pve-figure">
  <img src="../../images/documentation/pve/pve-1.png" width="558" height="602" loading="lazy" decoding="async" alt="Home Assistant PVE access form with separate User, Token ID and Token Secret fields." />
  <figcaption>PVE access credentials in Proxmox Extended Sensors. User, Token ID and Token Secret are entered as separate values.</figcaption>
</figure>

The integration can automatically detect the Proxmox node associated with the host address. Advanced configurations can disable automatic detection when the node needs to be specified manually.

### SSL verification

Proxmox Extended Sensors can verify the SSL certificate presented by the PVE server.

Enable certificate verification when the server uses a certificate that Home Assistant can validate correctly.

Environments using the default Proxmox self-signed certificate may require SSL verification to remain disabled unless the appropriate certificate trust has been configured.

Disabling verification should only be used for environments where you understand and trust the connection path.

### Choose what to monitor

After the connection has been validated, the configuration flow allows you to select the resources that should be exposed to Home Assistant.

You do not need to monitor every available resource.

Choose the nodes, virtual machines, containers, storage or supported monitoring options that are useful for your Home Assistant environment.

A focused selection keeps the resulting devices and entities easier to understand and reduces unnecessary monitoring.

The selection can be adjusted later if your environment or monitoring requirements change.

### Configuration can evolve

The initial setup does not need to represent the final monitoring configuration.

A practical approach is to start with the resources that matter most, confirm that the resulting devices and entities provide useful information, and then expand the configuration when a real need appears.

This is especially useful in larger Proxmox environments where exposing every possible resource would create a large number of Home Assistant entities.

### After configuration

Once setup is complete, Home Assistant creates the corresponding devices and entities for the selected PVE resources.

The following sections explain how that information is organized and what the different monitoring areas provide:

- [**Node monitoring**](#node-monitoring)
- [**VM & CT monitoring**](#vm-ct-monitoring)
- [**Hardware**](#hardware)
- [**Storage**](#storage)

If the connection succeeds but expected information is missing, see [**Troubleshooting**](#troubleshooting).
