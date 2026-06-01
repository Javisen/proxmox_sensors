"""API for Proxmox Extended Sensors."""

from typing import Any, Optional
import logging
import requests
import urllib3
from proxmoxer import ProxmoxAPI

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LOGGER = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when the API rejects the supplied credentials."""


class CannotConnect(Exception):
    """Raised when the API cannot be reached."""


class PermissionError(Exception):
    """Raised when credentials are valid but permissions are insufficient."""


def _raise_for_auth_or_permission(status_code: int | None, path: str) -> None:
    """Map only auth/permission statuses; other HTTP errors are not network errors."""
    if status_code == 401:
        raise AuthenticationError(f"Authentication failed for {path}")
    if status_code == 403:
        raise PermissionError(f"Permission denied for {path}")


def _extract_status_code(err: Exception) -> int | None:
    response = getattr(err, "response", None)
    if response is not None and getattr(response, "status_code", None):
        return response.status_code

    status_code = getattr(err, "status_code", None) or getattr(err, "status", None)
    if status_code:
        return int(status_code)

    message = str(err)
    for code in (401, 403):
        if str(code) in message:
            return code

    return None


class ProxmoxClient:
    def __init__(
        self,
        host: str,
        user: str,
        password: Optional[str] = None,
        token_id: Optional[str] = None,
        token_secret: Optional[str] = None,
        server_type: str = "PVE",
        port: Optional[int] = None,
        verify_ssl: bool = True,
    ):
        self._host = host
        self._user = user
        self._password = password
        self._token_id = token_id
        self._token_secret = token_secret
        self._server_type = server_type
        self._port = port
        self._verify_ssl = verify_ssl
        self._proxmox: Optional[ProxmoxAPI] = None

    def _build_client_sync(self):
        if self._server_type == "PBS":
            return

        port = self._port or 8006
        timeout_val = 30

        try:
            if self._token_id and self._token_secret:
                self._proxmox = ProxmoxAPI(
                    self._host,
                    user=self._user,
                    token_name=self._token_id,
                    token_value=self._token_secret,
                    verify_ssl=self._verify_ssl,
                    port=port,
                    timeout=timeout_val,
                )
            else:
                self._proxmox = ProxmoxAPI(
                    self._host,
                    user=self._user,
                    password=self._password,
                    verify_ssl=self._verify_ssl,
                    port=port,
                    timeout=timeout_val,
                )
        except Exception as err:
            LOGGER.error(
                "Failed to initialize Proxmoxer client on %s: %s", self._host, err
            )
            self._proxmox = None

    async def get_api_client(self, hass):
        if self._server_type == "PBS":
            return None

        if self._proxmox is None:
            await hass.async_add_executor_job(self._build_client_sync)

        return self._proxmox

    async def get(self, hass, path: str, raise_errors: bool = False) -> Any:
        if self._server_type == "PBS":
            return await hass.async_add_executor_job(
                self._pbs_request, "GET", path, None, raise_errors
            )

        proxmox = await self.get_api_client(hass)
        if proxmox is None:
            if raise_errors:
                raise CannotConnect(f"Unable to initialize client for {path}")
            return None

        try:
            return await hass.async_add_executor_job(proxmox.get, path)
        except Exception as err:
            if raise_errors:
                status_code = _extract_status_code(err)
                if status_code is not None:
                    _raise_for_auth_or_permission(status_code, path)
                    LOGGER.debug(
                        "PVE HTTP %s on validation endpoint %s", status_code, path
                    )
                    return None
                if isinstance(err, requests.exceptions.RequestException):
                    raise CannotConnect(f"PVE request failed for {path}") from err
                raise
            LOGGER.error("PVE GET error on %s: %s", path, err)
            return None

    async def post(self, hass, path: str, data=None) -> Any:
        proxmox = await self.get_api_client(hass)
        if proxmox is None:
            return None

        def _do_post():
            return proxmox.post(path, **(data or {}))

        try:
            return await hass.async_add_executor_job(_do_post)
        except Exception as err:
            LOGGER.error("PVE POST error on %s: %s", path, err)
            return None

    async def get_cluster_resources(self, hass):
        return await self.get(hass, "cluster/resources") or []

    async def get_cluster_tasks(self, hass):
        return await self.get(hass, "cluster/tasks") or []

    async def get_backup_jobs(self, hass):
        return await self.get(hass, "cluster/backup") or []

    async def get_nodes(self, hass):
        """Return nodes in cluster."""
        data = await self.get(hass, "nodes")
        return data or []

    async def get_node_ip(self, hass, node):
        """Get primary IPv4 of a node"""
        net = await self.get_node_network(hass, node)

        for iface in net or []:
            addr = iface.get("address")

            if addr and not addr.startswith("127.") and ":" not in addr:
                return addr

        return None

    async def get_node_status(self, hass, node: str):
        return await self.get(hass, f"nodes/{node}/status")

    async def get_node_updates(self, hass, node: str):
        return await self.get(hass, f"nodes/{node}/apt/update")

    async def get_node_network(self, hass, node: str):
        return await self.get(hass, f"nodes/{node}/network") or []

    async def get_vms(self, hass, node: str):
        return await self.get(hass, f"nodes/{node}/qemu") or []

    async def get_containers(self, hass, node: str):
        return await self.get(hass, f"nodes/{node}/lxc") or []

    async def get_container_status(self, hass, node: str, vmid: str):
        return await self.get(hass, f"nodes/{node}/lxc/{vmid}/status/current")

    async def get_qemu_status(self, hass, node: str, vmid: str):
        return await self.get(hass, f"nodes/{node}/qemu/{vmid}/status/current")

    async def get_lxc_status(self, hass, node: str, vmid: str):
        return await self.get(hass, f"nodes/{node}/lxc/{vmid}/status/current")

    async def get_vm_type(self, hass, node: str, vmid: str) -> str:
        vms = await self.get_vms(hass, node)
        if isinstance(vms, list):
            for vm in vms:
                if str(vm.get("vmid")) == str(vmid):
                    return "qemu"

        containers = await self.get_containers(hass, node)
        if isinstance(containers, list):
            for ct in containers:
                if str(ct.get("vmid")) == str(vmid):
                    return "lxc"

        return "unknown"

    async def get_vm_status(self, hass, node: str, vmid: str):
        vmtype = await self.get_vm_type(hass, node, vmid)
        if vmtype == "qemu":
            return await self.get_qemu_status(hass, node, vmid)
        if vmtype == "lxc":
            return await self.get_lxc_status(hass, node, vmid)
        return None

    async def get_storages(self, hass, node: str):
        return await self.get(hass, f"nodes/{node}/storage") or []

    async def get_disks(self, hass, node: str):
        return await self.get(hass, f"nodes/{node}/disks/list") or []

    async def control_vm(self, hass, node: str, vmid: str, command: str):
        valid_vm_commands = [
            "start",
            "stop",
            "shutdown",
            "reboot",
            "reset",
            "suspend",
            "resume",
            "hibernate",
        ]
        if command not in valid_vm_commands:
            LOGGER.error(f"Invalid VM command: {command}")
            return False

        if command == "hibernate":
            path = f"nodes/{node}/qemu/{vmid}/status/suspend"
            data = {"todisk": 1}
        else:
            path = f"nodes/{node}/qemu/{vmid}/status/{command}"
            data = {}

        if command in ["shutdown", "reboot"]:
            data["timeout"] = 60

        result = await self.post(hass, path, data)

        return result

    async def execute_vm_command(self, hass, node: str, vmid: str, command: str):
        return await self.control_vm(hass, node, vmid, command)

    async def execute_ct_command(self, hass, node: str, vmid: str, command: str):
        return await self.control_container(hass, node, vmid, command)

    async def execute_node_command(self, hass, node: str, command: str):
        if command == "reboot":
            return await self.reboot_node(hass, node)
        elif command == "shutdown":
            return await self.shutdown_node(hass, node)
        else:
            LOGGER.error(f"Invalid node command: {command}")
            return False

    async def control_container(self, hass, node: str, vmid: str, command: str):
        valid_ct_commands = ["start", "stop", "shutdown", "reboot"]
        if command not in valid_ct_commands:
            LOGGER.error(
                f"Invalid CT command: {command}. Valid commands: {valid_ct_commands}"
            )
            return False

        path = f"nodes/{node}/lxc/{vmid}/status/{command}"
        data = {}

        if command in ["shutdown", "reboot"]:
            data["timeout"] = 60

        result = await self.post(hass, path, data)

        return result

    async def shutdown_node(self, hass, node: str):
        path = f"nodes/{node}/status"
        data = {"command": "shutdown"}
        return await self.post(hass, path, data)

    async def reboot_node(self, hass, node: str):
        path = f"nodes/{node}/status"
        data = {"command": "reboot"}
        return await self.post(hass, path, data)

    async def get_lm_sensors_http(self, hass, node: str):
        url = f"http://{self._host}:9000/sensors"

        def _fetch():
            try:
                r = requests.get(url, timeout=5)
                r.raise_for_status()
                return r.json()
            except Exception:
                return {}

        return await hass.async_add_executor_job(_fetch)

    async def get_smart_data_http(self, hass, node: str):
        url = f"http://{self._host}:9000/smart"

        def _fetch():
            try:
                r = requests.get(url, timeout=15)
                r.raise_for_status()
                return r.json()
            except Exception:
                return {}

        return await hass.async_add_executor_job(_fetch)

    async def get_memory_http(self, hass, node: str):
        url = f"http://{self._host}:9000/memory"

        def _fetch():
            try:
                r = requests.get(url, timeout=15)
                r.raise_for_status()
                return r.json()
            except Exception:
                return {}

        return await hass.async_add_executor_job(_fetch)

    async def get_mounts(self, hass, node):
        return await hass.async_add_executor_job(self._get_mounts_sync)

    def _get_mounts_sync(self):
        url = f"http://{self._host}:9000/mounts"

        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception:
            return {}

    async def get_zfs_pools(self, hass, node):
        return await self.get(hass, f"nodes/{node}/disks/zfs") or []

    async def start_vzdump(
        self,
        hass,
        node: str,
        vmid: str,
        storage: str,
        notes: str = None,
        mode: str = "snapshot",
        compress: str = "zstd",
    ):
        if not node or not vmid or not storage:
            raise ValueError("node, vmid, and storage are required to start a backup")

        path = f"nodes/{node}/vzdump"
        if compress == "none":
            compress = "0"

        valid_modes = ["snapshot", "suspend", "stop"]
        if mode not in valid_modes:
            raise ValueError(
                f"Invalid mode: {mode}. Must be one of: {', '.join(valid_modes)}"
            )

        valid_compress = ["0", "1", "lzo", "gzip", "zstd", "none"]
        if compress not in valid_compress:
            raise ValueError(
                f"Invalid compression: {compress}. Must be one of: {', '.join(valid_compress)}"
            )

        data = {
            "vmid": vmid,
            "storage": storage,
            "mode": mode,
            "compress": compress,
        }

        if notes:
            data["notes-template"] = notes

        result = await self.post(hass, path, data)

        return result

    async def get_cluster_status(self, hass):
        """Return cluster status (name, quorum, version)."""
        data = await self.get(hass, "cluster/status") or []
        # The API returns a list; extract the item with type=="cluster"
        for item in data:
            if isinstance(item, dict) and item.get("type") == "cluster":
                return item
        return {}

    async def get_cluster_ha_status(self, hass):
        """Return current HA manager status."""
        return await self.get(hass, "cluster/ha/status/current") or {}

    async def get_cluster_firewall_options(self, hass):
        """Return cluster firewall options."""
        return await self.get(hass, "cluster/firewall/options") or {}

    def _pbs_request(
        self, method: str, path: str, data=None, raise_errors: bool = False
    ):
        port = self._port or 8007

        clean_host = (
            self._host.replace("https://", "")
            .replace("http://", "")
            .split("/")[0]
            .split(":")[0]
        )
        url = f"https://{clean_host}:{port}/api2/json/{path}"

        if not self._user or not self._token_secret:
            LOGGER.error("PBS token authentication requires user and token_secret")
            if raise_errors:
                raise AuthenticationError("PBS token authentication is incomplete")
            return None

        if self._token_id:
            if "!" in self._token_id:
                token_full = self._token_id
            else:
                token_full = f"{self._user}!{self._token_id}"
        else:
            LOGGER.error("PBS token_id is missing")
            if raise_errors:
                raise AuthenticationError("PBS token_id is missing")
            return None

        auth_header = f"PBSAPIToken {token_full}:{self._token_secret}"
        headers = {"Authorization": auth_header, "Accept": "application/json"}

        try:
            if method == "GET":
                r = requests.get(
                    url, headers=headers, verify=self._verify_ssl, timeout=15
                )
            else:
                r = requests.post(
                    url,
                    headers=headers,
                    json=(data or {}),
                    verify=self._verify_ssl,
                    timeout=15,
                )

            if raise_errors and r.status_code >= 400:
                _raise_for_auth_or_permission(r.status_code, path)
                LOGGER.debug(
                    "PBS HTTP %s on validation endpoint %s: %s",
                    r.status_code,
                    path,
                    r.text,
                )
                return None

            if r.status_code == 403:
                return None

            if r.status_code >= 400:
                LOGGER.error("PBS HTTP %s on %s: %s", r.status_code, path, r.text)
                return None

            return r.json().get("data")

        except (AuthenticationError, PermissionError, CannotConnect):
            raise
        except requests.exceptions.RequestException as err:
            if raise_errors:
                raise CannotConnect(f"PBS request failed for {path}") from err
            return None
        except Exception as err:
            if raise_errors:
                LOGGER.debug(
                    "PBS validation endpoint %s failed with %s: %s",
                    path,
                    type(err).__name__,
                    err,
                )
                raise
            return None

    async def pbs_get(self, hass, path: str) -> Any:
        return await hass.async_add_executor_job(self._pbs_request, "GET", path, None)

    async def pbs_post(self, hass, path: str, data=None) -> Any:
        return await hass.async_add_executor_job(
            self._pbs_request, "POST", path, data or {}
        )

    async def get_pbs_datastores(self, hass):
        data = await self.pbs_get(hass, "admin/datastore")
        return (
            [d["store"] for d in data if isinstance(d, dict) and "store" in d]
            if data
            else []
        )

    async def get_pbs_hostname(self, hass):
        """Get PBS hostname from status endpoint."""
        data = await self.pbs_get(hass, "status")

        if isinstance(data, dict):
            return data.get("hostname")

        return None

    async def get_pbs_datastore_status(self, hass, store: str):
        return await self.pbs_get(hass, f"admin/datastore/{store}/status") or {}

    async def get_pbs_datastore_usage(self, hass, store: str):
        return await self.pbs_get(hass, f"admin/datastore/{store}/gc") or {}

    async def get_pbs_tasks(self, hass):
        return await self.pbs_get(hass, "nodes/localhost/tasks") or []

    async def get_pbs_version(self, hass):
        return await self.pbs_get(hass, "version") or {}

    async def get_pbs_backup_list(self, hass, store: str):
        return await self.pbs_get(hass, f"admin/datastore/{store}/snapshots") or []

    async def get_pbs_node_status(self, hass):
        return await self.pbs_get(hass, "nodes/localhost/status") or {}

    async def get_pbs_gc(self, hass, store: str):
        return await self.pbs_get(hass, f"admin/datastore/{store}/gc") or {}

    async def get_pbs_snapshots(self, hass, store: str):
        return await self.pbs_get(hass, f"admin/datastore/{store}/snapshots") or []

    async def execute_pbs_node_command(self, hass, node, command):
        """Execute a command on PBS node (shutdown/reboot)."""
        try:
            path = f"nodes/{node}/status"
            data = {"command": command}

            result = await self.pbs_post(hass, path, data)
            return result is not None
        except Exception as e:
            LOGGER.error("Error executing PBS node command %s: %s", command, e)
            return False
