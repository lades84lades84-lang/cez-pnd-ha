# ČEZ PND – vývojová verze 0.2.0

Tato verze odděluje Playwright prohlížeč do samostatného Home Assistant App (doplňku) `ČEZ PND Bridge`. Vlastní integrace komunikuje s bridge přes lokální HTTP API. MQTT se nepoužívá.

## Proč je potřeba bridge
Playwright potřebuje odpovídající prohlížečové binárky. Samotná instalace Python balíčku do Home Assistant Core je nezajišťuje. Playwright vyžaduje samostatně instalovaný browser runtime (viz dokumentace Playwright). Proto je prohlížeč izolovaný v samostatném App kontejneru.

## Obsah
- `addon/cez_pnd_bridge`: Playwright + Chromium (Debian) + lokální HTTP API na portu 8099
- `custom_components/cez_pnd`: integrace HA, která vytváří senzory NT/VT, registry a úplnost dat

## Instalace bridge
1. Rozbal ZIP.
2. Přes Samba/SSH nahraj složku `addon/cez_pnd_bridge` do `/addons/cez_pnd_bridge`.
3. V HA otevři Nastavení → Aplikace → Obchod s aplikacemi → ⋮ → Znovu načíst.
4. Nainstaluj `ČEZ PND Bridge`.
5. V konfiguraci doplň e-mail, heslo a ID elektroměru `3000017121`.
6. Spusť doplněk a sleduj jeho log.

## Instalace integrace
Zkopíruj `custom_components/cez_pnd` do `/config/custom_components/cez_pnd` a restartuj Home Assistant.
Přidej integraci ČEZ PND. Adresa bridge je výchozí `http://cez-pnd-bridge:8099`.

## Test
- Bridge endpoint `GET http://cez-pnd-bridge:8099/health`
- Report endpoint `POST /api/report` volá PND API přes přihlášený browser context.
- Log nikdy nevypisuje heslo ani obsah cookies.

## Stav a omezení
Toto je první testovací implementace. Přihlašovací formulář se hledá podle běžných HTML polí; pokud ČEZ změní formulář nebo použije nestandardní selektory, bude nutné upravit `server.py`. Před živým testem nelze tvrdit, že přihlášení a získání dat už funguje. Ověření se provádí až v logu bridge a přes endpointy.
