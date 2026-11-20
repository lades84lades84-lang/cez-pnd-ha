import aiohttp

class BridgeError(Exception):
    pass

class CezPndBridge:
    def __init__(self, session, base_url, meter_id):
        self.session = session
        self.base_url = base_url
        self.meter_id = meter_id

    async def report(self, report_id, start, end):
        payload = {
            "report_id": report_id,
            "interval_from": start.strftime("%d.%m.%Y %H:%M"),
            "interval_to": end.strftime("%d.%m.%Y %H:%M"),
        }
        try:
            async with self.session.post(
                f"{self.base_url}/api/report", json=payload,
                timeout=aiohttp.ClientTimeout(total=90)
            ) as response:
                data = await response.json(content_type=None)
                if response.status >= 400:
                    message = data.get("error", f"Bridge HTTP {response.status}") if isinstance(data, dict) else f"Bridge HTTP {response.status}"
                    raise BridgeError(message)
                if not isinstance(data, dict):
                    raise BridgeError("Bridge vrátil neočekávaný formát.")
                return data
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise BridgeError(f"Nelze se spojit s ČEZ PND Bridge: {err}") from err
