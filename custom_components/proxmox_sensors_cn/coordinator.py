# ====== COORDINATOR — PROXMOX EXTENDED SENSORS ======

import logging
import asyncio
from datetime import timedelta, datetime, timezone
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_NODE, CONF_PLATFORM_TYPE
from .logic.guest_keys import make_guest_key, matches_selected_guest

_LOGGER = logging.getLogger(__name__)


def _normalize_api_dict(payload):
    """Normalize Proxmox API payloads that may be wrapped in {'data': ...}."""
    if isinstance(payload, dict):
        nested = payload.get("data")
        if isinstance(nested, dict):
            return nested
        return payload
    return {}


async def limited_task_func(func, *args):
    async with SEM:
        return await func(*args)


def _log_cluster_fetch_error(field: str, err: Exception) -> None:
    """Log non-fatal cluster fetch errors without failing the whole update."""
    _LOGGER.warning("Failed to fetch %s: %s", field, err)


def _to_iso_timestamp(value):
    """Convert Proxmox epoch timestamps to ISO-8601 strings."""
    if value in (None, ""):
        return None

    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _build_backup_jobs_payload(jobs, tasks):
    """Build a safe backup-jobs summary from cluster jobs and recent vzdump tasks."""
    if not isinstance(jobs, list):
        jobs = []

    if not isinstance(tasks, list):
        tasks = []
    else:
        tasks = sorted(
            tasks,
            key=lambda x: x.get("endtime") or x.get("starttime") or 0,
            reverse=True,
        )[:20]

    latest_task = None
    latest_task_time = 0

    for task in tasks:
        if not isinstance(task, dict):
            continue

        upid = task.get("upid", "")
        if "vzdump" not in upid:
            continue

        task_time = task.get("endtime") or task.get("starttime") or 0

        if task_time >= latest_task_time:
            latest_task = task
            latest_task_time = task_time

    normalized_jobs = []
    failed_jobs = 0
    last_run_ts = None
    recent_failed_ts = None
    now_ts = datetime.now(tz=timezone.utc).timestamp()

    for index, job in enumerate(jobs):
        if not isinstance(job, dict):
            continue

        matched_task = latest_task or {}

        starttime = matched_task.get("starttime")
        endtime = matched_task.get("endtime")
        run_ts = endtime or starttime

        duration = None
        if starttime is not None and endtime is not None:
            try:
                duration = max(int(endtime - starttime), 0)
            except (TypeError, ValueError):
                duration = None

        raw_status = matched_task.get("status")
        if isinstance(raw_status, str) and raw_status.lower() == "ok":
            last_status = "OK"
        elif raw_status:
            last_status = "error"
        else:
            last_status = "unknown"

        if last_status == "error":
            failed_jobs += 1
            if run_ts is not None and (
                recent_failed_ts is None or run_ts > recent_failed_ts
            ):
                recent_failed_ts = run_ts

        if run_ts is not None and (last_run_ts is None or run_ts > last_run_ts):
            last_run_ts = run_ts

        job_id = (
            job.get("id")
            or job.get("vmid")
            or job.get("job_id")
            or f"backup_job_{index}"
        )

        normalized_jobs.append(
            {
                "id": str(job_id),
                "node": job.get("node") or "cluster",
                "storage": job.get("storage") or job.get("dumpdir") or "unknown",
                "schedule": job.get("schedule") or "unknown",
                "last_status": last_status,
                "last_run": _to_iso_timestamp(run_ts),
                "duration": duration,
            }
        )

    state = "unknown"
    if normalized_jobs:
        if failed_jobs == 0 and all(
            job["last_status"] == "OK" for job in normalized_jobs
        ):
            state = "ok"
        elif failed_jobs > 1:
            state = "error"
        elif (
            failed_jobs == 1
            and recent_failed_ts is not None
            and (now_ts - recent_failed_ts) <= 86400
        ):
            state = "error"
        elif failed_jobs >= 1:
            state = "warning"
        else:
            state = "unknown"

    return {
        "state": state,
        "total_jobs": len(normalized_jobs),
        "failed_jobs": failed_jobs,
        "last_run": _to_iso_timestamp(last_run_ts),
        "jobs": normalized_jobs,
    }


async def create_proxmox_coordinator(hass, entry, client):

    data = entry.data
    node = data.get(CONF_NODE, "Proxmox")
    server_type = data.get(CONF_PLATFORM_TYPE, "PVE")

    selected_vms = data.get("selected_vms", [])
    selected_cts = data.get("selected_cts", [])
    selected_storage = data.get("selected_storage", [])

    enable_physical_disks = data.get("enable_physical_disks", True)
    enable_lm_sensors = data.get("enable_lm_sensors", True)
    enable_pbs_tasks = data.get("enable_pbs_tasks", True)
    enable_smart_monitoring = data.get("enable_smart_monitoring", True)

    enable_memory_monitoring = entry.options.get(
        "enable_memory_monitoring",
        entry.data.get("enable_memory_monitoring", True),
    )

    SEM = asyncio.Semaphore(5)

    async def limited_task(coro_func, *args):
        async with SEM:
            return await coro_func(*args)

    async def async_update_data():

        result = {"server_type": server_type}

        try:
            async with asyncio.timeout(30):

                # ========PBS==========

                if server_type == "PBS":

                    result["pbs_datastores"] = {}
                    result["pbs_snapshots"] = {}
                    result["pbs_gc"] = {}

                    selected = data.get("selected_storage")

                    if not selected:
                        actual_stores = await client.get_pbs_datastores(hass)
                    else:
                        actual_stores = selected

                    for store in actual_stores or []:

                        status = (
                            await client.get_pbs_datastore_status(hass, store) or {}
                        )
                        usage = await client.get_pbs_datastore_usage(hass, store) or {}
                        backups = await client.get_pbs_backup_list(hass, store) or []

                        backups_sorted = sorted(
                            backups, key=lambda x: x.get("backup-time", 0), reverse=True
                        )

                        last_backup = backups_sorted[0] if backups_sorted else None

                        backup_errors = [
                            b
                            for b in backups_sorted
                            if b.get("verification", {}).get("state") == "failed"
                        ]

                        try:
                            result["pbs_gc"][store] = (
                                await client.get_pbs_gc(hass, store) or {}
                            )
                        except Exception:
                            result["pbs_gc"][store] = {}

                        try:
                            result["pbs_snapshots"][store] = (
                                await client.get_pbs_snapshots(hass, store) or []
                            )
                        except Exception:
                            result["pbs_snapshots"][store] = []

                        result["pbs_datastores"][store] = {
                            **status,
                            **usage,
                            "backup_count": len(backups_sorted),
                            "backups": backups_sorted,
                            "last_backup": last_backup,
                            "backup_errors": backup_errors,
                        }

                    node_status = await client.get_pbs_node_status(hass)
                    result["pbs_node_status"] = (
                        node_status if isinstance(node_status, dict) else {}
                    )

                    version_info = await client.get_pbs_version(hass) or {}
                    result["pbs_version"] = version_info.get("version")
                    result["pbs_release"] = version_info.get("release")
                    result["pbs_auth_status"] = "OK" if version_info else "ERROR"

                    if enable_pbs_tasks:
                        tasks = await client.get_pbs_tasks(hass) or []
                        result["pbs_tasks"] = tasks if isinstance(tasks, list) else []
                    else:
                        result["pbs_tasks"] = []

                    result["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    return result

                # ==========PVE================

                if server_type == "PVE":

                    cluster_resources = []
                    cluster_status = {}
                    cluster_ha = {}
                    cluster_firewall = {}

                    cluster_results = await asyncio.gather(
                        client.get_cluster_resources(hass),
                        client.get_cluster_status(hass),
                        client.get_cluster_ha_status(hass),
                        client.get_cluster_firewall_options(hass),
                        return_exceptions=True,
                    )

                    if isinstance(cluster_results[0], Exception):
                        _log_cluster_fetch_error(
                            "cluster resources", cluster_results[0]
                        )
                    elif isinstance(cluster_results[0], list):
                        cluster_resources = cluster_results[0]

                    if isinstance(cluster_results[1], Exception):
                        _log_cluster_fetch_error("cluster status", cluster_results[1])
                    else:
                        cluster_status = _normalize_api_dict(cluster_results[1])

                    if isinstance(cluster_results[2], Exception):
                        _log_cluster_fetch_error(
                            "cluster HA status", cluster_results[2]
                        )
                    else:
                        cluster_ha = _normalize_api_dict(cluster_results[2])

                    if isinstance(cluster_results[3], Exception):
                        _log_cluster_fetch_error(
                            "cluster firewall options", cluster_results[3]
                        )
                    else:
                        cluster_firewall = _normalize_api_dict(cluster_results[3])

                    nodes = set()
                    node_status_map = {}

                    for r in cluster_resources:
                        if not isinstance(r, dict):
                            continue
                        if r.get("type") == "node":
                            node_name = r.get("node")
                            status = r.get("status", "unknown")
                            if node_name:
                                nodes.add(node_name)
                                node_status_map[node_name] = status

                    result["cluster_nodes"] = sorted(nodes) if nodes else [node]
                    result["node_status_map"] = (
                        node_status_map if node_status_map else {node: "unknown"}
                    )
                    result["cluster_status"] = cluster_status
                    result["cluster_resources"] = cluster_resources
                    result["cluster_ha"] = cluster_ha
                    result["cluster_firewall"] = cluster_firewall

                    # -------- Parallel node calls --------

                    tasks = [
                        (client.get_node_status, hass, node),
                        (client.get_node_updates, hass, node),
                        (client.get_node_network, hass, node),
                        (client.get_cluster_tasks, hass),
                        (client.get_vms, hass, node),
                        (client.get_containers, hass, node),
                        (client.get_storages, hass, node),
                        (client.get_zfs_pools, hass, node),
                        (client.get_disks, hass, node),
                        (client.get_mounts, hass, node),
                    ]

                    if enable_lm_sensors:
                        tasks.append((client.get_lm_sensors_http, hass, node))

                    if enable_smart_monitoring:
                        tasks.append((client.get_smart_data_http, hass, node))

                    if enable_memory_monitoring:
                        tasks.append((client.get_memory_http, hass, node))

                    results = await asyncio.gather(
                        *(limited_task(*task) for task in tasks),
                        return_exceptions=True,
                    )

                    idx = 0

                    # -------- Node status --------

                    node_status = results[idx]
                    idx += 1

                    normalized = {}
                    if isinstance(node_status, dict):
                        normalized = node_status.get("data", node_status)

                    result["node"] = normalized or {"status": "unknown"}

                    # -------- Node updates --------

                    updates = results[idx]
                    idx += 1

                    if isinstance(updates, Exception) or not isinstance(updates, list):
                        result["node_updates"] = {
                            "available": False,
                            "count": 0,
                            "packages": [],
                            "error": True,
                        }
                    else:
                        result["node_updates"] = {
                            "available": len(updates) > 0,
                            "count": len(updates),
                            "packages": updates,
                            "error": False,
                        }

                    # -------- Network --------

                    interfaces = results[idx]
                    idx += 1

                    if isinstance(interfaces, list):
                        rx = sum(i.get("rx_bytes", 0) for i in interfaces)
                        tx = sum(i.get("tx_bytes", 0) for i in interfaces)
                        result["node"]["network_rx"] = rx
                        result["node"]["network_tx"] = tx

                    # -------- Tasks --------

                    cluster_tasks = results[idx]
                    idx += 1

                    result["tasks"] = (
                        cluster_tasks if isinstance(cluster_tasks, list) else []
                    )

                    if result["tasks"]:
                        last = result["tasks"][0]
                        result["node"]["last_task"] = {
                            "status": last.get("status", "running"),
                            "type": last.get("type", "unknown"),
                            "user": last.get("user", "unknown"),
                            "id": last.get("id", "node"),
                            "endtime": last.get("endtime"),
                        }

                    # -------- VMs --------

                    vms = results[idx]
                    idx += 1

                    vms_dict = {}
                    for vm in vms or []:
                        vmid = vm.get("vmid")
                        if vmid is None:
                            continue
                        guest_key = make_guest_key(node, vmid)
                        if not matches_selected_guest(
                            selected_vms, node, vmid, guest_key
                        ):
                            continue
                        base = dict(vm)
                        base["node"] = node
                        base["guest_key"] = guest_key
                        for field in [
                            "cpu",
                            "mem",
                            "maxmem",
                            "disk",
                            "maxdisk",
                            "uptime",
                            "netin",
                            "netout",
                        ]:
                            base.setdefault(field, 0)
                        base.setdefault("status", "unknown")
                        vms_dict[guest_key] = base

                    result["vms"] = vms_dict

                    # -------- Containers --------

                    cts = results[idx]
                    idx += 1

                    cts_dict = {}
                    for ct in cts or []:
                        vmid = ct.get("vmid")
                        if vmid is None:
                            continue
                        guest_key = make_guest_key(node, vmid)
                        if not matches_selected_guest(
                            selected_cts, node, vmid, guest_key
                        ):
                            continue
                        base = dict(ct)
                        base["node"] = node
                        base["guest_key"] = guest_key
                        for field in [
                            "cpu",
                            "mem",
                            "maxmem",
                            "disk",
                            "maxdisk",
                            "uptime",
                            "netin",
                            "netout",
                        ]:
                            base.setdefault(field, 0)
                        base.setdefault("status", "unknown")
                        cts_dict[guest_key] = base

                    result["cts"] = cts_dict

                    # -------- Storage --------

                    storages = results[idx]
                    idx += 1

                    result["storage"] = {
                        st["storage"]: st
                        for st in storages or []
                        if isinstance(st, dict)
                        and "storage" in st
                        and (not selected_storage or st["storage"] in selected_storage)
                    }

                    # -------- ZFS --------

                    zfs_data = results[idx]
                    idx += 1

                    result["zfs_pools"] = (
                        {
                            pool.get("name"): pool
                            for pool in (zfs_data or [])
                            if isinstance(pool, dict) and pool.get("name")
                        }
                        if isinstance(zfs_data, list) and zfs_data
                        else {}
                    )

                    # -------- Node disks --------

                    disks = results[idx]
                    idx += 1

                    result["node_disks"] = (
                        [disk for disk in disks if isinstance(disk, dict)]
                        if isinstance(disks, list)
                        else []
                    )

                    # -------- MOUNTS --------

                    mounts_data = results[idx]
                    idx += 1

                    result["mounts"] = (
                        mounts_data if isinstance(mounts_data, dict) else {}
                    )

                    # -------- Disks --------

                    if enable_physical_disks:
                        result["disks"] = {
                            d.get("devpath", f"disk_{i}"): d
                            for i, d in enumerate(result["node_disks"])
                        }

                    # -------- LM Sensors --------

                    result["hardware"] = {}
                    if enable_lm_sensors:
                        lm = results[idx]
                        idx += 1
                        if isinstance(lm, dict):
                            for chip, values in lm.items():
                                if isinstance(values, dict):
                                    for k, v in values.items():
                                        result["hardware"][f"{chip}_{k}".lower()] = v

                    # -------- SMART --------

                    result["smart"] = {}
                    if enable_smart_monitoring:
                        smart_data = results[idx]
                        idx += 1
                        result["smart"][node] = (
                            smart_data if isinstance(smart_data, dict) else {}
                        )

                    # -------- Memory --------

                    result["memory"] = {}
                    if enable_memory_monitoring:
                        memory_data = results[idx]
                        if isinstance(memory_data, dict):
                            modules = memory_data.get("modules", [])
                            result["memory"][node] = {
                                "modules": modules,
                                "total_modules": memory_data.get(
                                    "total_modules", len(modules)
                                ),
                                "total_gb": memory_data.get("total_gb", 0),
                                "timestamp": memory_data.get("timestamp"),
                                "dimms": {
                                    module["locator"]: module
                                    for module in modules
                                    if "locator" in module
                                },
                            }
                        else:
                            result["memory"][node] = {
                                "modules": [],
                                "total_modules": 0,
                                "total_gb": 0,
                                "timestamp": None,
                                "dimms": {},
                            }

                    result["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    return result

        except Exception as err:
            _LOGGER.exception("Coordinator update failure")
            raise UpdateFailed(f"Update error: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"proxmox_{server_type.lower()}_{node}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=60),
    )

    coordinator.client = client
    coordinator.api = client

    return coordinator


async def create_cluster_coordinator(hass, entry, client):
    """Lightweight coordinator that only fetches cluster-level data."""

    async def async_update_cluster():
        result = {"server_type": "CLUSTER"}

        try:
            async with asyncio.timeout(20):
                (
                    cluster_resources,
                    cluster_status,
                    cluster_ha,
                    cluster_firewall,
                    backup_jobs,
                    backup_tasks,
                ) = await asyncio.gather(
                    client.get_cluster_resources(hass),
                    client.get_cluster_status(hass),
                    client.get_cluster_ha_status(hass),
                    client.get_cluster_firewall_options(hass),
                    client.get_backup_jobs(hass),
                    client.get_cluster_tasks(hass),
                    return_exceptions=True,
                )

                result["cluster_resources"] = (
                    cluster_resources if isinstance(cluster_resources, list) else []
                )
                result["cluster_status"] = (
                    _normalize_api_dict(cluster_status)
                    if not isinstance(cluster_status, Exception)
                    else {}
                )
                result["cluster_ha"] = (
                    _normalize_api_dict(cluster_ha)
                    if not isinstance(cluster_ha, Exception)
                    else {}
                )
                result["cluster_firewall"] = (
                    _normalize_api_dict(cluster_firewall)
                    if not isinstance(cluster_firewall, Exception)
                    else {}
                )
                result["backup_jobs"] = _build_backup_jobs_payload(
                    backup_jobs if not isinstance(backup_jobs, Exception) else [],
                    backup_tasks if not isinstance(backup_tasks, Exception) else [],
                )

        except Exception as err:
            raise UpdateFailed(f"Cluster update error: {err}")

        result["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return result

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"proxmox_cluster_{entry.data.get('cluster_name', 'unknown')}",
        update_method=async_update_cluster,
        update_interval=timedelta(seconds=60),
    )

    coordinator.client = client
    coordinator.api = client

    return coordinator
