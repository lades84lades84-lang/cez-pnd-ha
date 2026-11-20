"""Local Playwright bridge for ČEZ PND. Never logs credentials or cookies."""
import asyncio
import json
import logging
import os
from datetime import datetime
from aiohttp import web
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

_LOG = logging.getLogger("cez_pnd_bridge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PND_URL = "https://pnd.cezdistribuce.cz/cezpnd2/external/dashboard/view"
DATA_URL = "https://pnd.cezdistribuce.cz/cezpnd2/external/data"

class PndBrowser:
    def __init__(self, cfg):
        self.cfg = cfg
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.lock = asyncio.Lock()
        self.last_login = None
        self.authenticated = False

    async def start(self):
        self.playwright = await async_playwright().start()
        # Alpine Chromium is provided by the add-on image.
        self.browser = await self.playwright.chromium.launch(
            headless=self.cfg.get("headless", True),
            executable_path="/usr/bin/chromium",
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        self.context = await self.browser.new_context(
            ignore_https_errors=False,
            locale="cs-CZ"
        )
        self.page = await self.context.new_page()

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def _login(self):
        email = self.cfg["email"]
        password = self.cfg["password"]
        if not email or not password:
            raise RuntimeError("V nastavení doplňte e-mail a heslo k ČEZ PND.")

        _LOG.info("Otevírám přihlašovací stránku ČEZ PND.")
        await self.page.goto(PND_URL, wait_until="domcontentloaded", timeout=60000)

        # The login provider may render the form after one or more redirects.
        pwd = self.page.locator('input[type="password"]').first
        await pwd.wait_for(state="visible", timeout=45000)

        # Prefer semantic selectors; fallback to the first visible text/email input.
        user_candidates = [
            self.page.locator('input[type="email"]').first,
            self.page.locator('input[name="username"]').first,
            self.page.locator('input[name="j_username"]').first,
            self.page.locator('input[autocomplete="username"]').first,
        ]
        user = None
        for candidate in user_candidates:
            try:
                if await candidate.is_visible(timeout=800):
                    user = candidate
                    break
            except Exception:
                pass
        if user is None:
            texts = self.page.locator('input[type="text"]:visible')
            if await texts.count():
                user = texts.first
        if user is None:
            raise RuntimeError("Přihlašovací formulář se zobrazil, ale nenašel jsem pole pro e-mail.")

        await user.fill(email)
        await pwd.fill(password)

        submit_candidates = [
            self.page.locator('button[type="submit"]').first,
            self.page.locator('input[type="submit"]').first,
            self.page.get_by_role("button", name="Přihlásit", exact=False).first,
            self.page.get_by_role("button", name="Login", exact=False).first,
        ]
        submitted = False
        for candidate in submit_candidates:
            try:
                if await candidate.is_visible(timeout=700):
                    await candidate.click(timeout=5000)
                    submitted = True
                    break
            except Exception:
                pass
        if not submitted:
            await pwd.press("Enter")

        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
        except PlaywrightTimeoutError:
            pass

        # A successful session should be able to load the PND dashboard.
        await self.page.goto(PND_URL, wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_timeout(1200)
        if await self.page.locator('input[type="password"]').count():
            raise RuntimeError("ČEZ PND stále zobrazuje přihlašovací formulář. Zkontrolujte přihlašovací údaje.")
        self.last_login = datetime.now().isoformat(timespec="seconds")
        cookie_count = len(await self.context.cookies())
        _LOG.info("Přihlášení do ČEZ PND dokončeno; prohlížeč eviduje %s cookies.", cookie_count)

    async def ensure_session(self):
        async with self.lock:
            if self.page is None:
                raise RuntimeError("Prohlížeč není spuštěn.")
            try:
                # Test session by loading the dashboard and checking whether login is requested.
                await self.page.goto(PND_URL, wait_until="domcontentloaded", timeout=45000)
                if await self.page.locator('input[type="password"]').count():
                    await self._login()
            except Exception as err:
                _LOG.warning("Kontrola relace selhala (%s); zkusím nové přihlášení.", type(err).__name__)
                await self._login()

    async def report(self, report_id, start, end):
        async with self.lock:
            payload = {
                "format": "stats",
                "idAssembly": int(report_id),
                "idDeviceSet": None,
                "intervalFrom": start,
                "intervalTo": end,
                "electrometerId": self.cfg["electrometer_id"],
                "compareFrom": None,
                "opmId": None,
            }
            if not self.authenticated:
                await self._login_unlocked()
            for attempt in range(2):
                result = await self.page.evaluate(
                    """async ({url, payload}) => {
                        const response = await fetch(url, {
                          method: 'POST',
                          credentials: 'include',
                          headers: {'Content-Type': 'application/json;charset=UTF-8'},
                          body: JSON.stringify(payload)
                        });
                        return {status: response.status, text: await response.text()};
                    }""",
                    {"url": DATA_URL, "payload": payload}
                )
                if result["status"] in (401, 403) and attempt == 0:
                    _LOG.warning("PND odmítlo relaci; provádím nové přihlášení.")
                    self.authenticated = False
                    await self._login_unlocked()
                    continue
                if result["status"] < 200 or result["status"] >= 300:
                    raise RuntimeError(f"PND API vrátilo HTTP {result['status']}.")
                try:
                    data = json.loads(result["text"])
                except json.JSONDecodeError as err:
                    raise RuntimeError("PND API nevrátilo JSON (relace může být neplatná).") from err
                if not isinstance(data, dict):
                    raise RuntimeError("PND API vrátilo neočekávanou strukturu.")
                return data
            raise RuntimeError("Nepodařilo se obnovit přihlášení do PND.")

    async def _login_unlocked(self):
        email = self.cfg["email"]
        password = self.cfg["password"]
        if not email or not password:
            raise RuntimeError("V nastavení doplňte e-mail a heslo k ČEZ PND.")

        _LOG.info("Otevírám přihlašovací stránku ČEZ PND.")
        await self.page.goto(PND_URL, wait_until="domcontentloaded", timeout=60000)
        pwd = self.page.locator('input[type="password"]:visible').first
        await pwd.wait_for(state="visible", timeout=45000)

        user = None
        for selector in (
            'input[type="email"]:visible',
            'input[name="username"]:visible',
            'input[name="j_username"]:visible',
            'input[autocomplete="username"]:visible',
            'input[type="text"]:visible',
        ):
            candidate = self.page.locator(selector).first
            try:
                if await candidate.is_visible(timeout=700):
                    user = candidate
                    break
            except Exception:
                pass
        if user is None:
            raise RuntimeError("Nenašel jsem pole pro e-mail na přihlašovací stránce.")

        await user.fill(email)
        await pwd.fill(password)
        submitted = False
        for selector in ('button[type="submit"]:visible', 'input[type="submit"]:visible'):
            candidate = self.page.locator(selector).first
            try:
                if await candidate.is_visible(timeout=700):
                    await candidate.click(timeout=5000)
                    submitted = True
                    break
            except Exception:
                pass
        if not submitted:
            await pwd.press("Enter")

        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
        except PlaywrightTimeoutError:
            pass
        await self.page.goto(PND_URL, wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_timeout(1000)
        if await self.page.locator('input[type="password"]:visible').count():
            raise RuntimeError("Přihlášení nebylo úspěšné; PND stále žádá heslo.")
        self.last_login = datetime.now().isoformat(timespec="seconds")
        self.authenticated = True
        _LOG.info("Přihlášení do ČEZ PND dokončeno; prohlížeč eviduje %s cookies.", len(await self.context.cookies()))

async def main():
    cfg_path = "/data/options.json"
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    browser = PndBrowser(cfg)
    await browser.start()

    async def health(_request):
        return web.json_response({"ok": True, "service": "cez_pnd_bridge", "login_time": browser.last_login})

    async def report(request):
        try:
            body = await request.json()
            data = await browser.report(
                body["report_id"], body["interval_from"], body["interval_to"]
            )
            return web.json_response(data)
        except Exception as err:
            _LOG.error("Požadavek na PND selhal: %s", str(err))
            return web.json_response({"error": str(err)}, status=502)

    app = web.Application(client_max_size=2 * 1024 * 1024)
    app.router.add_get("/health", health)
    app.router.add_post("/api/report", report)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8099)
    await site.start()
    _LOG.info("Lokální ČEZ PND bridge naslouchá na portu 8099.")
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
