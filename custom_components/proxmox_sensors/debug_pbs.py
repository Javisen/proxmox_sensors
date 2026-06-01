import logging
_LOGGER = logging.getLogger(__name__)

async def run(hass, client, store):
    status = await client.get_pbs_datastore_status(hass, store)
    _LOGGER.warning("📦 PBS STATUS for '%s': %s", store, status)

    backups = await client.get_pbs_backup_list(hass, store)
    _LOGGER.warning("🗂️ PBS BACKUPS for '%s': %s", store, backups)

    tasks = await client.get_pbs_tasks(hass)
    _LOGGER.warning("🧩 PBS TASKS: %s", tasks)
