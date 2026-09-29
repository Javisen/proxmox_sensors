Proxmox Extended Sensors V5 uses **API Token authentication** for PBS connections.

A dedicated account is recommended instead of using a general administrative login.

PBS and PVE use separate authentication systems. A user created in Proxmox VE should not be assumed to exist automatically in Proxmox Backup Server.

### Create a dedicated PBS user

Create a dedicated account in Proxmox Backup Server for the Home Assistant integration.

Use the appropriate PBS realm for that account.

Keeping the integration on its own account makes its access easier to identify, manage and revoke without affecting other administrative users.

### Assign permissions

The permissions required depend on which PBS features you intend to expose to Home Assistant.

Monitoring datastore and backup information can require less access than executing maintenance operations.

For a full-feature PBS installation, the project documentation has traditionally used the **Administrator** role at `/` for the dedicated integration account.

This is a broad role.

Advanced users can choose a more restrictive permission model, but they should verify every feature they intend to use, especially:

- datastore visibility;
- backup information;
- task information;
- Garbage Collection;
- Prune;
- Verify;
- Sync.

A successful authentication does not necessarily prove that the account has permission to use every PBS endpoint required by optional functionality.

### Create the API Token

Create an API Token for the dedicated PBS account and save the generated secret securely.

The token secret is a credential.

Do not include it in screenshots, diagnostic logs, issues or other public material.

If a token is recreated, remember that Home Assistant must be updated with the new secret.

### Credentials used in Home Assistant

The PBS setup expects:

- **User** — the complete PBS user including its realm;
- **Token ID** — the short token name, or the complete API token identifier when required by the provider;
- **Token Secret** — the generated token secret.

Enter these values separately in the Proxmox Extended Sensors configuration flow.

Once authentication is prepared, continue with [**Configuration**](#configuration) to add the PBS server.
