from datetime import datetime, time, timedelta
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from .api import BridgeError, CezPndBridge
from .const import REPORT_NT, REPORT_VT, REPORT_REGISTERS
from .parser import tariff_total, tariff_completeness, register_value

_LOGGER = logging.getLogger(__name__)

class CezPndCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, session, base_url, meter_id, interval):
        super().__init__(hass, _LOGGER, name="ČEZ PND", update_interval=interval)
        self.bridge = CezPndBridge(session, base_url, meter_id)
        self.meter_id = meter_id

    async def _async_update_data(self):
        now = dt_util.now()
        start = datetime.combine(now.date(), time.min)
        end = start + timedelta(days=1)
        try:
            nt = await self.bridge.report(REPORT_NT, start, end)
            vt = await self.bridge.report(REPORT_VT, start, end)
            # PND's daily register report may not have today's range yet.
            # Request it anyway; the returned raw ranges are kept for parser validation.
            regs = await self.bridge.report(REPORT_REGISTERS, start, end)
        except BridgeError as err:
            raise UpdateFailed(str(err)) from err
        ncomp = tariff_completeness(nt, "Nízký tarif")
        vcomp = tariff_completeness(vt, "Vysoký tarif")
        comps = [v for v in (ncomp, vcomp) if v is not None]
        return {
            "nt_today_kwh": tariff_total(nt, "Nízký tarif"),
            "vt_today_kwh": tariff_total(vt, "Vysoký tarif"),
            "nt_completeness": ncomp,
            "vt_completeness": vcomp,
            "completeness": min(comps) if comps else None,
            "nt_register_kwh": register_value(regs, f"+E_NT/{self.meter_id}"),
            "vt_register_kwh": register_value(regs, f"+E_VT/{self.meter_id}"),
            "import_register_kwh": register_value(regs, f"+E/{self.meter_id}"),
            "export_register_kwh": register_value(regs, f"-E/{self.meter_id}"),
            "last_update": now,
        }
