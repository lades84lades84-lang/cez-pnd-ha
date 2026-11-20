from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN, PLATFORMS, CONF_BRIDGE_URL, CONF_ELECTROMETER_ID, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .coordinator import CezPndCoordinator

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    coordinator = CezPndCoordinator(
        hass, session, entry.data[CONF_BRIDGE_URL].rstrip("/"),
        entry.data[CONF_ELECTROMETER_ID],
        timedelta(minutes=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return ok

PLATFORMS = ["sensor"]
