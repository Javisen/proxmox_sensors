# ====== COORDINATOR — PROXMOX EXTENDED SENSORS ======

import logging
import asyncio
import requests
from datetime import timedelta, datetime, timezone
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_NODE, CONF_PLATFORM_TYPE
from .api import AuthenticationError, CannotConnect, PermissionError as ProxmoxPermissionError
from .logic.guest_keys import (
    find_guest_node_in_resources,
    make_guest_key,
    matches_selected_guest,
)
from .logic.guest_agent import collect_vm_disk_usage
from .logic.guest_selection import (
    get_effective_guest_selections,
    get_entry_guest_selection,
    set_effective_guest_selections,
)
from .logic.pdm import build_pdm_remotes, merge_pdm_sections, merge_pdm_updates

_LOGGER = logging.getLogger(__name__)


def is_pbs_temporary_unavailable(error):
    while error is not None:
        if isinstance(error, (TimeoutError, requests.exceptions.Timeout)):
            return True
        if isinstance(error, CannotConnect):
            cause = error.__cause__
            if isinstance(cause, (requests.exceptions.ConnectionError, OSError)) and not isinstance(
                cause, requests.exceptions.SSLError
            ):
                return True
        error = error.__cause__
    return False


def is_pbs_configuration_error(error):
    while error is not None:
        if isinstance(error, (AuthenticationError, ProxmoxPermissionError)):
            return True
        error = error.__cause__
    return False


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


def _build_backup_jobs_payload(
    jobs,
    tasks,
    *,
    jobs_available=True,
    tasks_available=True,
):
    """Build an authoritative cluster backup summary."""
    current_jobs = jobs if jobs_available and isinstance(jobs, list) else None
    current_tasks = tasks if tasks_available and isinstance(tasks, list) else None

    completed_tasks = []
    if current_tasks is not None:
        completed_tasks = [
            task
            for task in current_tasks
            if isinstance(task, dict)
            and task.get("type") == "vzdump"
            and task.get("endtime") not in (None, "")
        ]

    statuses = [
        task.get("status")
        for task in completed_tasks
        if task.get("status") not in (None, "")
    ]
    if any(str(status).lower() != "ok" for status in statuses):
        state = "error"
    elif statuses:
        state = "ok"
    else:
        state = "unknown"

    endtimes = []
    for task in completed_tasks:
        try:
            endtimes.append(float(task["endtime"]))
        except (KeyError, TypeError, ValueError):
            continue

    return {
        "state": state,
        "total_jobs": len(current_jobs) if current_jobs is not None else None,
        "last_task_run": _to_iso_timestamp(max(endtimes)) if endtimes else None,
        "jobs_available": current_jobs is not None,
        "tasks_available": current_tasks is not None,
    }


async def create_proxmox_coordinator(hass, entry, client):

    data = entry.data
    node = data.get(CONF_NODE, "Proxmox")
    server_type = data.get(CONF_PLATFORM_TYPE, "PVE")

    selected_vms = get_entry_guest_selection(entry, "selected_vms", [])
    selected_cts = get_entry_guest_selection(entry, "selected_cts", [])
    selected_storage = data.get("selected_storage", [])

    enable_physical_disks = data.get("enable_physical_disks", True)
    enable_lm_sensors = data.get("enable_lm_sensors", True)
    enable_pbs_tasks = data.get("enable_pbs_tasks", True)
    enable_smart_monitoring = data.get("enable_smart_monitoring", True)
    enable_guest_agent_metrics = entry.options.get(
        "enable_guest_agent_metrics",
        entry.data.get("enable_guest_agent_metrics", False),
    )

    enable_memory_monitoring = entry.options.get(
        "enable_memory_monitoring",
        entry.data.get("enable_memory_monitoring", True),
    )

    SEM = asyncio.Semaphore(5)

    async def limited_task(coro_func, *args):
        async with SEM:
            async with asyncio.timeout(10):
                return await coro_func(*args)

    sidecar_endpoints = {
        client.get_lm_sensors_http: "sensors",
        client.get_smart_data_http: "smart",
        client.get_memory_http: "memory",
        client.get_ksm_http: "ksm",
        client.get_mounts: "mounts",
    }
    _sidecar_health = {
        endpoint: {
            "status": "unknown",
            "last_attempt": None,
            "last_success": None,
            "response_time_ms": None,
            "consecutive_failures": 0,
            "error_type": None,
            "last_error": None,
        }
        for endpoint in sidecar_endpoints.values()
    }
    _sidecar_cycle_status = {}

    async def sidecar_task(endpoint, coro_func, *args):
        """Observe the existing call without changing its result or exceptions."""
        attempted = datetime.now(timezone.utc).isoformat()
        started = asyncio.get_running_loop().time()

        def record(error=None):
            previous = _sidecar_health[endpoint]
            succeeded = error is None
            status = "ok" if succeeded else "error"
            _sidecar_health[endpoint] = {
                "status": status,
                "last_attempt": attempted,
                "last_success": datetime.now(timezone.utc).isoformat()
                if succeeded else previous["last_success"],
                # Observed call latency includes the existing semaphore wait.
                "response_time_ms": round(
                    (asyncio.get_running_loop().time() - started) * 1000, 2
                ),
                "consecutive_failures": 0 if succeeded
                else previous["consecutive_failures"] + 1,
                # A successful call clears the endpoint's error details.
                "error_type": None if succeeded else type(error).__name__,
                "last_error": None if succeeded
                else (str(error) or type(error).__name__)[:512],
            }
            _sidecar_cycle_status[endpoint] = status
            _LOGGER.debug("Sidecar health node=%s endpoint=%s health=%s",
                          node, endpoint, _sidecar_health[endpoint])

        try:
            value = await limited_task(coro_func, *args)
        except Exception as err:
            record(err)
            raise
        else:
            record()
            return value

    ONBOOT_REFRESH_EVERY_N_CYCLES = 10
    _onboot_cache: dict = {}
    _onboot_cycle = {"n": 0}
    _last_good_non_guest: dict = {}
    _last_good_guests: dict = {"vms": {}, "cts": {}}
    _last_good_guest_agent: dict = {}
    _last_good_cluster: dict = {}
    _last_good_pbs: dict = {}
    # This capability belongs to this coordinator instance only. Reloading an
    # entry creates a new coordinator and deliberately permits a new probe.
    _pbs_node_status_capability = "unknown"

    def _remember_non_guest_section(section: str, value):
        _last_good_non_guest[section] = value
        return value

    def _last_good_non_guest_section(section: str, fallback):
        return _last_good_non_guest.get(section, fallback)

    def _remember_cluster_section(section: str, value):
        _last_good_cluster[section] = value
        return value

    def _last_good_cluster_section(section: str, fallback):
        return _last_good_cluster.get(section, fallback)

    def _pbs_cache_key(section: str, store: str | None = None):
        return (section, store) if store is not None else section

    def _remember_pbs_section(section: str, value, store: str | None = None):
        _last_good_pbs[_pbs_cache_key(section, store)] = value
        return value

    def _last_good_pbs_section(section: str, fallback, store: str | None = None):
        return _last_good_pbs.get(_pbs_cache_key(section, store), fallback)

    def _cleanup_defaults():
        return {
            "hardware": False,
            "memory": False,
            "storage": False,
            "zfs_pools": False,
            "node_disks": False,
            "vms": False,
            "cts": False,
            "pbs_datastores": False,
            "cluster_ha": False,
        }

    def _mark_cleanup_confirmed(result: dict, section: str, confirmed: bool = True):
        result.setdefault("_cleanup_confirmed", _cleanup_defaults())[section] = confirmed

    async def _pbs_preserved_call(
        section: str, fallback, coro_func, *args, store: str | None = None
    ):
        key = _pbs_cache_key(section, store)
        try:
            value = await limited_task(coro_func, *args, True)
        except Exception as err:
            if (isinstance(err, (AuthenticationError, ProxmoxPermissionError))
                    or is_pbs_temporary_unavailable(err)):
                raise

            _LOGGER.warning("PBS: Failed to fetch %s: %s", section, err)
            return _last_good_pbs.get(key, fallback)

        return _remember_pbs_section(section, value, store=store)

    def _configured_pve_nodes():
        return {
            (e.data.get(CONF_NODE) or "").lower()
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.data.get(CONF_PLATFORM_TYPE) == "PVE"
        }

    def _filter_preserved_guests(kind: str, guest_map: dict, cluster_resources):
        filtered = {}
        configured_nodes = _configured_pve_nodes()

        for guest_key, guest_data in guest_map.items():
            vmid = guest_data.get("vmid")
            if vmid is None:
                filtered[guest_key] = guest_data
                continue

            located_node = find_guest_node_in_resources(
                cluster_resources, kind, vmid
            )
            if (
                located_node
                and located_node.lower() != node.lower()
                and located_node.lower() in configured_nodes
            ):
                continue

            filtered[guest_key] = guest_data

        return filtered

    def _build_guest_map(raw_guests, kind: str, selected_values):
        guest_map = {}
        for guest in raw_guests or []:
            vmid = guest.get("vmid")
            if vmid is None:
                continue
            guest_key = make_guest_key(node, vmid)
            if not matches_selected_guest(selected_values, node, vmid, guest_key):
                continue
            base = dict(guest)
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
            base["onboot"] = _onboot_cache.get(guest_key)
            guest_map[guest_key] = base

        _last_good_guests["vms" if kind == "vm" else "cts"] = guest_map
        return guest_map

    def _preserved_guest_map(kind: str, cluster_resources_ok: bool, cluster_resources):
        section = "vms" if kind == "vm" else "cts"
        guest_map = dict(_last_good_guests.get(section, {}))
        if cluster_resources_ok:
            filtered = _filter_preserved_guests(kind, guest_map, cluster_resources)
            _last_good_guests[section] = filtered
            return filtered
        return guest_map

    async def _refresh_onboot_batch(guest_specs):
        """guest_specs: list of (guest_type, node, vmid, guest_key).
        Fetches /config for all of them concurrently (bounded by SEM) and
        updates _onboot_cache in place."""

        async def _fetch_one(guest_type, g_node, vmid, guest_key):
            try:
                if guest_type == "vm":
                    config = await limited_task(
                        client.get_vm_config, hass, g_node, vmid
                    )
                else:
                    config = await limited_task(
                        client.get_ct_config, hass, g_node, vmid
                    )
                _onboot_cache[guest_key] = bool(int((config or {}).get("onboot", 0)))
            except Exception as err:
                _LOGGER.debug(
                    "Could not refresh onboot config for %s: %s", guest_key, err
                )

        if guest_specs:
            await asyncio.gather(*(_fetch_one(*spec) for spec in guest_specs))

    async def _refresh_guest_agent_metrics(raw_vms, selected_values):
        """Fetch independent per-VM QGA metrics while preserving last-good data."""
        return await collect_vm_disk_usage(
            raw_vms,
            guest_key_for=lambda vmid: make_guest_key(node, vmid),
            is_selected=lambda vm, guest_key: matches_selected_guest(
                selected_values, node, vm["vmid"], guest_key
            ),
            fetch_fsinfo=lambda vmid: limited_task(
                client.get_vm_fsinfo, hass, node, vmid
            ),
            last_good=_last_good_guest_agent,
        )

    async def async_update_data():
        nonlocal _pbs_node_status_capability

        result = {"server_type": server_type, "_cleanup_confirmed": _cleanup_defaults()}

        try:
            async with asyncio.timeout(30):

                # ========PBS==========

                if server_type == "PBS":

                    result["pbs_datastores"] = {}
                    result["pbs_snapshots"] = {}
                    result["pbs_gc"] = {}

                    selected = data.get("selected_storage")

                    if selected is None:
                        try:
                            actual_stores = await limited_task(
                                client.get_pbs_datastores, hass, True
                            )
                        except Exception as err:
                            if (isinstance(err, (AuthenticationError, ProxmoxPermissionError))
                                    or is_pbs_temporary_unavailable(err)):
                                raise
                            _LOGGER.warning(
                                "PBS: Failed to fetch %s: %s",
                                "pbs_datastore_names",
                                err,
                            )
                            actual_stores = _last_good_pbs_section(
                                "pbs_datastore_names", []
                            )
                        else:
                            actual_stores = _remember_pbs_section(
                                "pbs_datastore_names", actual_stores
                            )
                            _mark_cleanup_confirmed(result, "pbs_datastores")
                    else:
                        actual_stores = selected
                        _mark_cleanup_confirmed(result, "pbs_datastores")

                    for store in actual_stores or []:

                        status = await _pbs_preserved_call(
                            "pbs_datastore_status",
                            {},
                            client.get_pbs_datastore_status,
                            hass,
                            store,
                            store=store,
                        )
                        usage = await _pbs_preserved_call(
                            "pbs_datastore_usage",
                            {},
                            client.get_pbs_datastore_usage,
                            hass,
                            store,
                            store=store,
                        )
                        backups = await _pbs_preserved_call(
                            "pbs_backup_list",
                            [],
                            client.get_pbs_backup_list,
                            hass,
                            store,
                            store=store,
                        )

                        backups_sorted = sorted(
                            backups, key=lambda x: x.get("backup-time", 0), reverse=True
                        )

                        last_backup = backups_sorted[0] if backups_sorted else None

                        backup_errors = [
                            b
                            for b in backups_sorted
                            if b.get("verification", {}).get("state") == "failed"
                        ]

                        result["pbs_gc"][store] = await _pbs_preserved_call(
                            "pbs_gc",
                            {},
                            client.get_pbs_gc,
                            hass,
                            store,
                            store=store,
                        )

                        result["pbs_snapshots"][store] = backups

                        result["pbs_datastores"][store] = {
                            **status,
                            **usage,
                            "backup_count": len(backups_sorted),
                            "backups": backups_sorted,
                            "last_backup": last_backup,
                            "backup_errors": backup_errors,
                        }

                    if _pbs_node_status_capability == "denied":
                        result["pbs_node_status"] = None
                    else:
                        try:
                            node_status = await limited_task(
                                client.get_pbs_node_status, hass, True
                            )
                        except ProxmoxPermissionError:
                            _pbs_node_status_capability = "denied"
                            _LOGGER.info(
                                "PBS node status is unavailable due to missing permission; "
                                "it will not be retried until this entry is reloaded"
                            )
                            result["pbs_node_status"] = None
                        else:
                            _pbs_node_status_capability = "available"
                            result["pbs_node_status"] = (
                                node_status if isinstance(node_status, dict) else {}
                            )

                    version_info = await _pbs_preserved_call(
                        "pbs_version_info", {}, client.get_pbs_version, hass
                    )
                    result["pbs_version"] = version_info.get("version")
                    result["pbs_release"] = version_info.get("release")
                    result["pbs_auth_status"] = "OK" if version_info else "ERROR"

                    if enable_pbs_tasks:
                        tasks = await _pbs_preserved_call(
                            "pbs_tasks", [], client.get_pbs_tasks, hass
                        )
                        result["pbs_tasks"] = tasks if isinstance(tasks, list) else []
                    else:
                        result["pbs_tasks"] = []

                    # PBS configured jobs
                    prune_jobs = await _pbs_preserved_call(
                        "pbs_prune_jobs", [], client.get_pbs_prune_jobs, hass
                    )
                    verify_jobs = await _pbs_preserved_call(
                        "pbs_verify_jobs", [], client.get_pbs_verify_jobs, hass
                    )
                    sync_jobs = await _pbs_preserved_call(
                        "pbs_sync_jobs", [], client.get_pbs_sync_jobs, hass
                    )

                    result["pbs_jobs"] = {
                        "prune": prune_jobs if isinstance(prune_jobs, list) else [],
                        "verify": verify_jobs if isinstance(verify_jobs, list) else [],
                        "sync": sync_jobs if isinstance(sync_jobs, list) else [],
                    }

                    result["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    return result

                # ==========PVE================

                if server_type == "PVE":
                    _sidecar_cycle_status.clear()

                    cluster_resources = []
                    cluster_status = {}
                    cluster_ha = {}
                    cluster_firewall = {}

                    cluster_results = await asyncio.gather(
                        limited_task(client.get_cluster_resources, hass, True),
                        limited_task(client.get_cluster_status, hass, True),
                        limited_task(client.get_cluster_ha_status, hass, True),
                        limited_task(
                            client.get_cluster_firewall_options, hass, True
                        ),
                        return_exceptions=True,
                    )

                    cluster_resources_ok = not isinstance(
                        cluster_results[0], Exception
                    )

                    if isinstance(cluster_results[0], Exception):
                        _log_cluster_fetch_error(
                            "cluster resources", cluster_results[0]
                        )
                        cluster_resources = _last_good_cluster_section(
                            "cluster_resources", []
                        )
                    elif isinstance(cluster_results[0], list):
                        cluster_resources = _remember_cluster_section(
                            "cluster_resources", cluster_results[0]
                        )

                    if isinstance(cluster_results[1], Exception):
                        _log_cluster_fetch_error("cluster status", cluster_results[1])
                        cluster_status = _last_good_cluster_section(
                            "cluster_status", {}
                        )
                    else:
                        cluster_status = _remember_cluster_section(
                            "cluster_status", _normalize_api_dict(cluster_results[1])
                        )
                        fresh_cluster_id = cluster_status.get("name")
                        if (
                            cluster_status.get("type") == "cluster"
                            and isinstance(fresh_cluster_id, str)
                            and fresh_cluster_id.strip()
                            and entry.data.get("cluster_id") != fresh_cluster_id
                        ):
                            # Only fresh cluster/status evidence, never last-good
                            # fallback. No entry update/reload listener is registered.
                            hass.config_entries.async_update_entry(
                                entry,
                                data={**entry.data, "cluster_id": fresh_cluster_id},
                            )

                    if isinstance(cluster_results[2], Exception):
                        _log_cluster_fetch_error(
                            "cluster HA status", cluster_results[2]
                        )
                        cluster_ha = _last_good_cluster_section("cluster_ha", {})
                    else:
                        cluster_ha = _remember_cluster_section(
                            "cluster_ha", _normalize_api_dict(cluster_results[2])
                        )
                        _mark_cleanup_confirmed(result, "cluster_ha")

                    if isinstance(cluster_results[3], Exception):
                        _log_cluster_fetch_error(
                            "cluster firewall options", cluster_results[3]
                        )
                        cluster_firewall = _last_good_cluster_section(
                            "cluster_firewall", {}
                        )
                    else:
                        cluster_firewall = _remember_cluster_section(
                            "cluster_firewall",
                            _normalize_api_dict(cluster_results[3]),
                        )

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

                    result["cluster_resources_ok"] = cluster_resources_ok

                    cluster_id = (
                        cluster_status.get("name")
                        if isinstance(cluster_status, dict)
                        else None
                    )
                    if cluster_id:
                        _remember_cluster_section("cluster_id", cluster_id)

                    result["cluster_id"] = cluster_id or _last_good_cluster_section(
                        "cluster_id", None
                    )
                    (
                        effective_selected_vms,
                        effective_selected_cts,
                    ) = get_effective_guest_selections(
                        hass,
                        entry,
                        result["cluster_id"],
                        selected_vms,
                        selected_cts,
                    )
                    set_effective_guest_selections(
                        result, effective_selected_vms, effective_selected_cts
                    )

                    # -------- Parallel node calls --------

                    tasks = [
                        (client.get_node_status, hass, node),
                        (client.get_node_updates, hass, node),
                        (client.get_node_network, hass, node),
                        (client.get_cluster_tasks, hass),
                        (client.get_vms, hass, node, True),
                        (client.get_containers, hass, node, True),
                        (client.get_storages, hass, node, True),
                        (client.get_zfs_pools, hass, node, True),
                    ]

                    if enable_physical_disks:
                        tasks.append((client.get_disks, hass, node, True))

                    tasks.append((client.get_mounts, hass, node, True))

                    if enable_smart_monitoring:
                        tasks.append((client.get_smart_data_http, hass, node, True))

                    if enable_memory_monitoring:
                        tasks.append((client.get_memory_http, hass, node, True))
                    tasks.append((client.get_ksm_http, hass, node, True))

                    results = await asyncio.gather(
                        *(sidecar_task(sidecar_endpoints[task[0]], *task)
                          if task[0] in sidecar_endpoints else limited_task(*task)
                          for task in tasks),
                        return_exceptions=True,
                    )

                    lm_sensors_data = None
                    if enable_lm_sensors:
                        try:
                            lm_sensors_data = await sidecar_task(
                                "sensors", client.get_lm_sensors_http, hass, node, True
                            )
                        except Exception as err:
                            _log_cluster_fetch_error("lm sensors", err)
                            lm_sensors_data = err
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

                    cts = results[idx]
                    idx += 1

                    _onboot_cycle["n"] += 1
                    should_refresh_onboot = (
                        _onboot_cycle["n"] % ONBOOT_REFRESH_EVERY_N_CYCLES == 0
                    )

                    onboot_specs = []
                    if not isinstance(vms, Exception):
                        for vm in vms or []:
                            vmid = vm.get("vmid")
                            if vmid is None:
                                continue
                            guest_key = make_guest_key(node, vmid)
                            if guest_key not in _onboot_cache or should_refresh_onboot:
                                onboot_specs.append(("vm", node, vmid, guest_key))
                    if not isinstance(cts, Exception):
                        for ct in cts or []:
                            vmid = ct.get("vmid")
                            if vmid is None:
                                continue
                            guest_key = make_guest_key(node, vmid)
                            if guest_key not in _onboot_cache or should_refresh_onboot:
                                onboot_specs.append(("ct", node, vmid, guest_key))

                    await _refresh_onboot_batch(onboot_specs)

                    if enable_guest_agent_metrics and not isinstance(vms, Exception):
                        (
                            result["guest_agent_disk_usage"],
                            result["guest_agent_metrics_status"],
                        ) = await _refresh_guest_agent_metrics(
                            vms, effective_selected_vms
                        )
                    elif enable_guest_agent_metrics:
                        result["guest_agent_disk_usage"] = dict(
                            _last_good_guest_agent
                        )
                        result["guest_agent_metrics_status"] = {
                            guest_key: "inventory_error"
                            for guest_key in _last_good_guest_agent
                        }
                    else:
                        result["guest_agent_disk_usage"] = {}
                        result["guest_agent_metrics_status"] = {}

                    if isinstance(vms, Exception):
                        result["vms"] = _preserved_guest_map(
                            "vm", result["cluster_resources_ok"], cluster_resources
                        )
                    else:
                        result["vms"] = _build_guest_map(
                            vms, "vm", effective_selected_vms
                        )
                        _mark_cleanup_confirmed(result, "vms")

                    if isinstance(cts, Exception):
                        result["cts"] = _preserved_guest_map(
                            "ct", result["cluster_resources_ok"], cluster_resources
                        )
                    else:
                        result["cts"] = _build_guest_map(
                            cts, "ct", effective_selected_cts
                        )
                        _mark_cleanup_confirmed(result, "cts")


                    # -------- Storage --------

                    storages = results[idx]
                    idx += 1

                    if isinstance(storages, Exception):
                        result["storage"] = _last_good_non_guest_section("storage", {})
                    else:
                        result["storage"] = _remember_non_guest_section(
                            "storage",
                            {
                                st["storage"]: st
                                for st in storages or []
                                if isinstance(st, dict)
                                and "storage" in st
                                and (
                                    selected_storage is None
                                    or st["storage"] in selected_storage
                                )
                            },
                        )
                        _mark_cleanup_confirmed(result, "storage")

                    # -------- ZFS --------

                    zfs_data = results[idx]
                    idx += 1

                    if isinstance(zfs_data, Exception):
                        result["zfs_pools"] = _last_good_non_guest_section(
                            "zfs_pools", {}
                        )
                    else:
                        result["zfs_pools"] = _remember_non_guest_section(
                            "zfs_pools",
                            {
                                pool.get("name"): pool
                                for pool in (zfs_data or [])
                                if isinstance(pool, dict) and pool.get("name")
                            }
                            if isinstance(zfs_data, list)
                            else {},
                        )
                        _mark_cleanup_confirmed(result, "zfs_pools")

                    # -------- Node disks --------

                    if not enable_physical_disks:
                        # Not fetched, so nothing polls the disks. Confirm the
                        # empty section so any old disk entities are cleaned up.
                        result["node_disks"] = []
                        _mark_cleanup_confirmed(result, "node_disks")
                    else:
                        disks = results[idx]
                        idx += 1

                        if isinstance(disks, Exception):
                            result["node_disks"] = _last_good_non_guest_section(
                                "node_disks", []
                            )
                        else:
                            result["node_disks"] = _remember_non_guest_section(
                                "node_disks",
                                (
                                    [disk for disk in disks if isinstance(disk, dict)]
                                    if isinstance(disks, list)
                                    else []
                                ),
                            )
                            _mark_cleanup_confirmed(result, "node_disks")

                    # -------- MOUNTS --------

                    mounts_data = results[idx]
                    idx += 1

                    if isinstance(mounts_data, Exception):
                        result["mounts"] = _last_good_non_guest_section("mounts", {})
                    else:
                        result["mounts"] = _remember_non_guest_section(
                            "mounts",
                            mounts_data if isinstance(mounts_data, dict) else {},
                        )

                    # -------- Disks --------

                    if enable_physical_disks:
                        result["disks"] = _remember_non_guest_section(
                            "disks",
                            {
                                d.get("devpath", f"disk_{i}"): d
                                for i, d in enumerate(result["node_disks"])
                            },
                        )

                    # -------- SMART --------

                    result["smart"] = {}
                    if enable_smart_monitoring:
                        smart_data = results[idx]
                        idx += 1
                        if isinstance(smart_data, Exception):
                            result["smart"] = _last_good_non_guest_section(
                                "smart", {node: {}}
                            )
                        else:
                            result["smart"] = _remember_non_guest_section(
                                "smart",
                                {
                                    node: (
                                        smart_data
                                        if isinstance(smart_data, dict)
                                        else {}
                                    )
                                },
                            )

                    # -------- Memory --------

                    result["memory"] = {}
                    if enable_memory_monitoring:
                        memory_data = results[idx]
                        if isinstance(memory_data, Exception):
                            result["memory"] = _last_good_non_guest_section(
                                "memory",
                                {
                                    node: {
                                        "modules": [],
                                        "total_modules": 0,
                                        "total_gb": 0,
                                        "timestamp": None,
                                        "dimms": {},
                                    }
                                },
                            )
                        elif isinstance(memory_data, dict):
                            modules = memory_data.get("modules", [])
                            result["memory"] = _remember_non_guest_section(
                                "memory",
                                {
                                    node: {
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
                                },
                            )
                            _mark_cleanup_confirmed(result, "memory")

                        else:
                            result["memory"] = _remember_non_guest_section(
                                "memory",
                                {
                                    node: {
                                        "modules": [],
                                        "total_modules": 0,
                                        "total_gb": 0,
                                        "timestamp": None,
                                        "dimms": {},
                                    }
                                },
                            )
                            _mark_cleanup_confirmed(result, "memory")

                    ksm_data = results[-1]
                    result["ksm_status"] = (
                        ksm_data if isinstance(ksm_data, dict) and not isinstance(ksm_data, Exception)
                        else {"available": False, "error": "KSM data is unavailable"}
                    )
                    ram_total = result.get("node", {}).get("memory", {}).get("total")
                    if isinstance(ram_total, (int, float)) and ram_total > 0:
                        result["ksm_status"]["ram_total_bytes"] = ram_total

                    # -------- LM Sensors --------

                    result["hardware"] = {}

                    if enable_lm_sensors:
                        lm = lm_sensors_data

                        if isinstance(lm, Exception):
                            result["hardware"] = _last_good_non_guest_section(
                                "hardware", {}
                            )
                        elif isinstance(lm, dict):
                            for chip, values in lm.items():
                                if isinstance(values, dict):
                                    for k, v in values.items():
                                        result["hardware"][f"{chip}_{k}".lower()] = v
                            result["hardware"] = _remember_non_guest_section(
                                "hardware", result["hardware"]
                            )
                            _mark_cleanup_confirmed(result, "hardware")
                        else:
                            result["hardware"] = _remember_non_guest_section(
                                "hardware", {}
                            )
                            _mark_cleanup_confirmed(result, "hardware")

                    result["sidecar_health"] = {
                        endpoint: dict(health) for endpoint, health in _sidecar_health.items()
                    }
                    statuses = set(_sidecar_cycle_status.values())
                    result["sidecar_status"] = (
                        "unknown" if not statuses else
                        "ok" if statuses == {"ok"} else
                        "error" if statuses == {"error"} else "degraded"
                    )
                    _LOGGER.debug("Sidecar health node=%s global=%s consulted=%s",
                                  node, result["sidecar_status"], _sidecar_cycle_status)
                    result["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    return result

        except Exception as err:
            if server_type == "PBS":
                if is_pbs_temporary_unavailable(err):
                    raise UpdateFailed(f"PBS temporarily unavailable: {err}") from err
                _LOGGER.exception("Coordinator update failure")
                raise UpdateFailed(f"Update error: {err}") from err
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
    SEM = asyncio.Semaphore(5)
    _last_good_cluster = {}

    def _cluster_cleanup_defaults():
        return {
            "hardware": False,
            "memory": False,
            "storage": False,
            "zfs_pools": False,
            "node_disks": False,
            "vms": False,
            "cts": False,
            "pbs_datastores": False,
            "cluster_ha": False,
        }

    async def limited_task(coro_func, *args):
        async with SEM:
            async with asyncio.timeout(10):
                return await coro_func(*args)

    async def replication_task():
        # Share the existing ten-second replication budget across both stages,
        # including semaphore waits, leaving the global timeout unchanged.
        deadline = asyncio.get_running_loop().time() + 10
        try:
            async with asyncio.timeout_at(deadline):
                inventory = await limited_task(client.get_cluster_replication, hass)
        except Exception as err:
            inventory = err
        inventory_ok = isinstance(inventory, list)
        inventory = _cluster_list_result("cluster_replication", inventory)
        sources = sorted({
            job["source"] for job in inventory
            if isinstance(job, dict) and isinstance(job.get("source"), str)
            and job["source"]
        })

        async def node_runtime(source):
            async with asyncio.timeout_at(deadline):
                return await limited_task(client.get_node_replication, hass, source)

        responses = await asyncio.gather(
            *(node_runtime(source) for source in sources), return_exceptions=True
        )
        # Copy the mapping and replace whole node snapshots, including [].
        cache = dict(_last_good_cluster_section("replication_runtime_by_node", {}))
        runtime_ok = {}
        for source, response in zip(sources, responses):
            runtime_ok[source] = isinstance(response, list)
            if runtime_ok[source]:
                cache[source] = response
            elif isinstance(response, Exception):
                _log_cluster_fetch_error(f"replication runtime on {source}", response)
        _remember_cluster_section("replication_runtime_by_node", cache)
        runtime_by_source = {
            source: {row["id"]: row for row in cache.get(source, [])
                     if isinstance(row, dict) and isinstance(row.get("id"), str)}
            for source in sources
        }
        jobs = {}
        for job in inventory:
            if not isinstance(job, dict) or not isinstance(job.get("id"), str):
                continue
            source = job.get("source")
            runtime = runtime_by_source.get(source, {}).get(job["id"])
            jobs[job["id"]] = {
                **(runtime or {}), **job,
                "inventory_fresh": inventory_ok,
                "runtime_fresh": runtime_ok.get(source, False),
                "runtime_present": runtime is not None,
            }
        return {
            "cluster_replication": inventory,
            "cluster_replication_ok": inventory_ok,
            "cluster_replication_jobs": jobs,
            "cluster_replication_runtime_ok": runtime_ok,
        }

    def _remember_cluster_section(key, value):
        _last_good_cluster[key] = value
        return value

    def _last_good_cluster_section(key, fallback):
        return _last_good_cluster.get(key, fallback)

    def _cluster_log_name(key):
        return {
            "cluster_resources": "cluster resources",
            "cluster_status": "cluster status",
            "cluster_ha": "cluster HA status",
            "cluster_firewall": "cluster firewall options",
            "cluster_qdevice": "cluster QDevice",
            "backup_jobs_raw": "backup jobs",
            "cluster_tasks": "cluster tasks",
            "cluster_replication": "cluster replication",
        }.get(key, key)

    def _cluster_list_result(key, value):
        if isinstance(value, Exception):
            _log_cluster_fetch_error(_cluster_log_name(key), value)
            return _last_good_cluster_section(key, [])
        if isinstance(value, list):
            return _remember_cluster_section(key, value)
        return _remember_cluster_section(key, [])

    def _cluster_dict_result(key, value):
        if isinstance(value, Exception):
            _log_cluster_fetch_error(_cluster_log_name(key), value)
            return _last_good_cluster_section(key, {})
        return _remember_cluster_section(key, _normalize_api_dict(value))

    async def async_update_cluster():
        result = {
            "server_type": "CLUSTER",
            "_cleanup_confirmed": _cluster_cleanup_defaults(),
        }

        try:
            async with asyncio.timeout(20):
                (
                    cluster_resources,
                    cluster_status,
                    cluster_ha,
                    cluster_firewall,
                    backup_jobs,
                    backup_tasks,
                    cluster_replication,
                    cluster_qdevice,
                ) = await asyncio.gather(
                    limited_task(client.get_cluster_resources, hass, True),
                    limited_task(client.get_cluster_status, hass, True),
                    limited_task(client.get_cluster_ha_status, hass, True),
                    limited_task(client.get_cluster_firewall_options, hass, True),
                    limited_task(client.get_backup_jobs, hass, True),
                    limited_task(client.get_cluster_tasks, hass, True),
                    replication_task(),
                    limited_task(client.get_cluster_qdevice, hass, True),
                    return_exceptions=True,
                )

                result["cluster_resources"] = _cluster_list_result(
                    "cluster_resources", cluster_resources
                )
                result["cluster_status"] = _cluster_dict_result(
                    "cluster_status", cluster_status
                )
                result["cluster_ha"] = _cluster_dict_result("cluster_ha", cluster_ha)
                result["_cleanup_confirmed"]["cluster_ha"] = not isinstance(
                    cluster_ha, Exception
                )
                result["cluster_firewall"] = _cluster_dict_result(
                    "cluster_firewall", cluster_firewall
                )
                result["cluster_qdevice"] = _cluster_dict_result(
                    "cluster_qdevice", cluster_qdevice
                )
                result["cluster_qdevice_ok"] = not isinstance(
                    cluster_qdevice, Exception
                )
                backup_jobs_raw = _cluster_list_result("backup_jobs_raw", backup_jobs)
                result["cluster_tasks"] = _cluster_list_result(
                    "cluster_tasks", backup_tasks
                )
                if isinstance(cluster_replication, Exception):
                    raise cluster_replication
                result.update(cluster_replication)

                _LOGGER.debug(
                    "Cluster replication: ok=%s jobs=%s",
                    result["cluster_replication_ok"],
                    result["cluster_replication"],
                )
                
                result["backup_jobs"] = _build_backup_jobs_payload(
                    backup_jobs_raw,
                    result["cluster_tasks"],
                    jobs_available=isinstance(backup_jobs, list),
                    tasks_available=isinstance(backup_tasks, list),
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


async def create_pdm_coordinator(hass, entry, client):
    """Create the PDM coordinator using the integration's polling model."""
    semaphore = asyncio.Semaphore(5)
    last_good = {}

    async def limited_task(coro_func, *args):
        async with semaphore:
            async with asyncio.timeout(15):
                return await coro_func(*args)

    async def async_update_pdm():
        async with asyncio.timeout(25):
            responses = await asyncio.gather(
                limited_task(client.get_pdm_version, hass),
                limited_task(client.get_pdm_remotes, hass),
                limited_task(client.get_pdm_resources, hass),
                limited_task(client.get_pdm_status, hass),
                limited_task(client.get_pdm_subscriptions, hass),
                limited_task(client.get_pdm_updates, hass),
                return_exceptions=True,
            )
        keys = ("version", "remotes", "resources", "status", "subscriptions")
        sections, sections_ok = merge_pdm_sections(last_good, keys, responses[:5])
        for key, response in zip(keys, responses[:5]):
            if isinstance(response, Exception) and key in last_good:
                _LOGGER.warning("PDM: retaining last-good %s after API error", key)

        for required in ("remotes", "status"):
            if sections[required] is None:
                error = responses[keys.index(required)]
                raise UpdateFailed(f"PDM {required} unavailable: {error}") from error
        resources = sections["resources"] if sections["resources"] is not None else []
        subscriptions = (
            sections["subscriptions"] if sections["subscriptions"] is not None else []
        )
        updates, updates_endpoint_fresh, updates_snapshot_complete = merge_pdm_updates(
            last_good,
            responses[5],
            sections["remotes"],
            sections_ok["remotes"],
        )
        sections_ok["updates"] = updates_endpoint_fresh
        if not updates_snapshot_complete and "updates" in last_good:
            _LOGGER.warning("PDM: retaining last-good updates after incomplete snapshot")
        return {
            "server_type": "PDM",
            "pdm_version": sections["version"] or {},
            "pdm_remote_inventory": sections["remotes"],
            "pdm_resources": resources,
            "pdm_status": sections["status"],
            "pdm_subscriptions": subscriptions,
            "pdm_updates": updates,
            "pdm_updates_snapshot_complete": updates_snapshot_complete,
            "pdm_remotes": build_pdm_remotes(
                sections["remotes"], sections["status"], resources, subscriptions
            ),
            "pdm_sections_ok": sections_ok,
            "pdm_sections_available": {
                key: key in last_good for key in (*keys, "updates")
            },
            "_cleanup_confirmed": {"pdm_remotes": sections_ok["remotes"]},
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"proxmox_pdm_{entry.entry_id}",
        update_method=async_update_pdm,
        update_interval=timedelta(seconds=60),
    )
    coordinator.client = client
    coordinator.api = client
    coordinator.pdm_display_name = entry.title
    return coordinator
