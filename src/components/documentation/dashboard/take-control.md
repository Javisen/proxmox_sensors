Home Assistant allows you to **Take Control** of the generated dashboard.

This converts the automatically maintained dashboard into a configuration that you can edit directly using the normal Home Assistant dashboard tools.

For users who want to reorganize the interface manually, this is the easiest customization method.

<figure class="pve-figure">
  <img src="../../images/documentation/dashboard/dashboard-5.png" width="782" height="490" loading="lazy" decoding="async" alt="Home Assistant Take control dialog warning that the dashboard will no longer be automatically updated." />
  <figcaption>Take Control — Home Assistant warns that taking control converts the automatically maintained dashboard into a manually managed configuration.</figcaption>
</figure>

### What you can change

After taking control, you can use the normal Home Assistant dashboard editor to:

- move cards and sections;
- remove information you do not want;
- add additional Proxmox Extended Sensors entities;
- add your own cards;
- add entities from other Home Assistant integrations;
- reorganize the layout;
- create your own visual hierarchy;
- adapt the dashboard to the particular way you use Home Assistant.

No JavaScript knowledge is required for this type of customization.

### What changes after Take Control

Taking control also changes who is responsible for maintaining the dashboard.

Once you take control, the dashboard is no longer dynamically managed by the automatic generator.

The automatic behaviour described in [**Automatic Dashboard**](#automatic-dashboard) is therefore lost.

For example:

- newly monitored guests will no longer necessarily be added automatically;
- guests removed from monitoring will no longer automatically disappear from your manually controlled configuration;
- migrated VMs and containers will no longer automatically move between node sections;
- conditional sections will no longer be managed dynamically by the generator;
- future structural improvements to the generated dashboard will not automatically modify your manually controlled version.

This is expected behaviour.

After **Take Control**, the dashboard configuration belongs to the user and Home Assistant preserves the manual configuration instead of allowing the automatic strategy to rebuild it.

### Automatic mode or Take Control?

Choose according to what matters most in your environment.

#### Stay in automatic mode if you want:

- minimal maintenance;
- automatic guest discovery and removal;
- automatic response to guest migration;
- conditional sections based on available features;
- the dashboard to remain aligned with supported generator changes.

#### Take Control if you want:

- complete visual editing through Home Assistant;
- your own card arrangement;
- additional entities or integrations in the same dashboard;
- a layout that differs substantially from the generated design;
- manual control to be more important than automatic maintenance.

Neither mode is inherently better.

They solve different needs.

The important point is to understand that **Take Control exchanges automatic maintenance for manual customization**.

### Before taking control

If you only want to inspect or use the generated dashboard, there is no need to take control.

Do not take control simply because Home Assistant offers the option.

The automatic dashboard is intentionally designed to work without manual editing.

If you later decide that a custom layout is more important, you can then choose Take Control knowing what behaviour will change.
