PDM connections use **API Token authentication**. Password authentication is not offered by the current PDM configuration flow.

Use a dedicated PDM account and token for Proxmox Extended Sensors. Home Assistant requires the user including its realm, the Token ID and the Token Secret as separate values.

The token secret is a credential. Never include it in screenshots, logs, issues or other public material.

### Access requirements

The token must be able to read the configured remote inventory and aggregate Datacenter status. Additional read access is needed for detailed resources, subscription state, version information and the update summary.

The exact least-privilege PDM role and ACL recipe is still pending documentation. Until that contract has been validated for the supported PDM version, do not present an unverified permission set as sufficient for every sensor.

If authentication succeeds but a data area is missing, compare the token's permissions with the affected feature before recreating the connection.
