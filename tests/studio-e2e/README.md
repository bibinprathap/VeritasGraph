# VeritasGraph Studio — Playwright E2E tests

End-to-end browser tests for the **live** VeritasGraph Studio UI, driven by
[Playwright](https://playwright.dev).

By default they run against the public entry point
<https://bibinprathap.github.io/VeritasGraph/studio/>, which meta-refresh
redirects to the live Cloudflare-tunnelled Studio. The tests follow that
redirect automatically.

## What they cover

| Spec | Checks |
|---|---|
| Shell & navigation | App title renders; **10** nav sections present, in order; every section switches; **no "Headroom"** text; "Veritasroom context budget" label present |
| KPIs | The four KPI cards populate with real values (not the `—` placeholder); **Last build** shows a real timestamp or "no deploys yet" |
| Tools | Connected-tools count is a small, loopback-only number (≤ 10), not the old inflated 16/18 |
| Playground | Agent selector populates; sending a message returns a reply in the chat log |
| Agents (write) | *Opt-in* create + delete of a throwaway agent (skipped unless `RUN_WRITE_TESTS=1`) |

Write tests are **skipped by default** so runs against the shared demo never
create clutter.

## Setup

```bash
cd tests/studio-e2e
npm install
npm run install:browsers      # downloads Chromium
```

## Run

```bash
# Against the live GitHub Pages / tunnel (default)
npm test

# Headed (watch the browser)
npm run test:headed

# Interactive UI mode
npm run test:ui

# Against a local backend instead of the live demo
STUDIO_URL=http://127.0.0.1:8200/studio npm test

# Against a specific tunnel
STUDIO_URL=https://your-tunnel.trycloudflare.com/studio npm test

# Include the create/delete agent test
RUN_WRITE_TESTS=1 npm test
```

## Reports

```bash
npm run report        # open the last HTML report
```

Failures capture a screenshot, video, and Playwright trace automatically
(`playwright-report/` and `test-results/`).

## Notes

- The live demo runs over a Cloudflare tunnel with a hard **100s** edge timeout,
  so timeouts here are deliberately generous.
- If the tunnel is offline, run against a local backend with `STUDIO_URL` (see
  the repo's studio startup command).
