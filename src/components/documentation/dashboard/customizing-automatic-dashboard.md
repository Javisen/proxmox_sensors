[Take Control](#take-control) is the recommended customization method for users who want to edit the dashboard through Home Assistant.

There is, however, another possibility for advanced users who specifically want to change the generated dashboard while preserving its automatic behaviour.

### Changing the generator

Users who want to modify the generated dashboard without taking control can modify:

`frontend/proxmox-dashboard.js`

This file contains the JavaScript responsible for generating the automatic dashboard.

Changing the generator can alter the automatic layout or behaviour while retaining the dynamic model instead of converting the dashboard into a manually maintained Home Assistant configuration.

### Advanced users only

Editing `proxmox-dashboard.js` is intended for users who understand JavaScript and are comfortable maintaining their own modifications.

If a user chooses to modify the generator, they are responsible for understanding how their changes interact with:

- automatic resource discovery;
- conditional sections;
- guest placement;
- guest migration;
- future dashboard changes;
- updates to the distributed frontend files.

For most users, **Take Control** is the appropriate method when manual customization is more important than automatic maintenance.

Modify `frontend/proxmox-dashboard.js` only when you specifically want to change the automatic generator itself while preserving its dynamic behaviour.

### Updates and custom changes

Changes made directly to the distributed JavaScript should be treated as custom project modifications.

When updating the dashboard, review your changes before replacing files or applying a newer version.

A future dashboard version may change the generator internally.

Maintaining a modified generator therefore requires more technical involvement than either using the automatic dashboard unchanged or taking control through Home Assistant.
