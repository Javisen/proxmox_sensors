"""PBS Actions for Proxmox Extended Sensors."""

import logging

_LOGGER = logging.getLogger(__name__)

BASE = "admin/datastore"


async def run_gc(client, hass, datastore: str):
    _LOGGER.info("PBS: Running GC in %s", datastore)
    endpoint = f"{BASE}/{datastore}/gc"
    return await client.pbs_post(hass, endpoint)


async def run_prune(client, hass, datastore: str):
    _LOGGER.info("PBS: Running automatic PRUNE in %s", datastore)

    snapshots = await client.pbs_get(hass, f"{BASE}/{datastore}/snapshots")
    if not snapshots:
        _LOGGER.warning("PBS: There are no snapshots in %s", datastore)
        return None

    groups = set()
    for snap in snapshots:
        btype = snap.get("backup-type")
        bid = snap.get("backup-id")
        if btype and bid:
            groups.add((btype, bid))

    results = []
    for btype, bid in groups:
        endpoint = f"{BASE}/{datastore}/prune"
        data = {"backup-type": btype, "backup-id": bid, "keep-last": 1}
        res = await client.pbs_post(hass, endpoint, data)
        results.append(res)

    return results


async def run_verify(client, hass, datastore: str):
    _LOGGER.info("PBS: Running automatic VERIFY on %s", datastore)

    snapshots = await client.pbs_get(hass, f"{BASE}/{datastore}/snapshots")
    if not snapshots:
        _LOGGER.warning("PBS: There are no snapshots in %s", datastore)
        return None

    groups = set()
    for snap in snapshots:
        btype = snap.get("backup-type")
        bid = snap.get("backup-id")
        if btype and bid:
            groups.add((btype, bid))

    results = []
    for btype, bid in groups:
        endpoint = f"{BASE}/{datastore}/verify"
        data = {"backup-type": btype, "backup-id": bid, "backup-time": 0}
        res = await client.pbs_post(hass, endpoint, data)
        results.append(res)

    return results


async def run_sync(client, hass, datastore: str):
    _LOGGER.info("PBS: Running automatic SYNC in %s", datastore)

    remotes = await client.pbs_get(hass, "remote")
    if not remotes:
        _LOGGER.warning("PBS: No remotes are configured in PBS")
        return None

    results = []

    for remote in remotes:
        name = remote.get("name")
        stores = remote.get("store", [])

        for store in stores:
            endpoint = f"{BASE}/{datastore}/sync"
            data = {"remote": name, "remote-store": store}
            res = await client.pbs_post(hass, endpoint, data)
            results.append(res)

    return results
