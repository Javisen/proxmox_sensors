PDM exposes each configured PVE or PBS environment as a remote child device beneath the PDM root device.

A PVE remote represents one complete PVE cluster or one standalone PVE installation, not an individual node. One PDM server can manage multiple PVE remotes as well as independent PBS remotes.

### Remote Status

**Remote Status** shows the state reported by PDM. Its attributes include the remote type, subscription state when available and whether the status section was refreshed successfully in the current poll.

### Remote Overview

**Remote Overview** reports the total resources associated with that remote. Its attributes summarize the discovered inventory and aggregate CPU, memory and storage capacity available from the resource data.

Remotes are discovered dynamically. A temporary API error retains the last valid information and does not prove that a remote was removed. Removal is reconciled only from a fresh, valid remote inventory.
