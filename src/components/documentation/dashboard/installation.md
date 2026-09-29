The Proxmox Extended Sensors dashboard is optional and is installed separately from the integration.

The integration provides the Home Assistant devices and entities.

The dashboard provides the automatic visual interface that organizes those entities.

The integration can be used without the dashboard.

### Requirements

Before installing the dashboard, make sure you have:

- **Proxmox Extended Sensors**
- **Card Mod**

Card Mod is available through HACS.

See the official <a href="https://github.com/thomasloven/lovelace-card-mod" target="_blank" rel="noopener noreferrer">Card Mod project</a>.

<figure class="pve-figure">
  <img src="../../images/documentation/dashboard/dashboard-8.png" width="565" height="357" loading="lazy" decoding="async" alt="Card Mod project installation view in HACS." />
  <figcaption>Card Mod — the automatic dashboard requires Card Mod, available through HACS.</figcaption>
</figure>

### Install Card Mod

If Card Mod is not already installed:

1. Open **HACS**.
2. Search for **Card Mod**.
3. Install it.
4. Restart or reload Home Assistant if required by the Card Mod installation.



### Add the dashboard resource

Add the following Lovelace resource as a **JavaScript Module**:

`/proxmox_sensors/proxmox-dashboard.js`

The resource must be registered as a JavaScript module.

<figure class="pve-figure">
  <img src="../../images/documentation/dashboard/dashboard-2.png" width="577" height="459" loading="lazy" decoding="async" alt="Home Assistant Add new resource dialog with /proxmox_sensors/proxmox-dashboard.js entered as a JavaScript module." />
  <figcaption>Dashboard resource — add <code>proxmox-dashboard.js</code> as a JavaScript module in Home Assistant.</figcaption>
</figure>

### Reload the browser

After adding the resource, reload the Home Assistant frontend.

If the dashboard option does not appear immediately, perform a hard browser refresh to make sure the latest JavaScript resource is being loaded.

### Create the dashboard

In Home Assistant, open:

**Settings → Dashboards → Add dashboard → Community**

Select:

**Proxmox Extended Sensors**

<figure class="pve-figure">
  <img src="../../images/documentation/dashboard/dashboard-3.png" width="674" height="715" loading="lazy" decoding="async" alt="Home Assistant Add dashboard dialog with Proxmox Extended Sensors selected under Community dashboards." />
  <figcaption>Community dashboard — select Proxmox Extended Sensors to create the automatically generated dashboard from your configured Proxmox resources.</figcaption>
</figure>

Home Assistant will create the dashboard using the Proxmox Extended Sensors community strategy.

The generated dashboard uses the entities currently exposed by the integration and builds the appropriate PVE, PBS and Cluster content automatically.

### Keep the dashboard automatic

After creating it, no manual card configuration is required.

As long as you do not use **Take Control**, the dashboard remains managed automatically and can continue adapting to changes in the integration.

The following section explains that automatic behaviour in detail.
