# QA Pro — API Tester

A small, dependency-free visual API tester. Pick a method, enter a URL, set
your headers / auth / body, hit **Send**, and see the raw JSON response —
status, timing, size, response headers, and a syntax-highlighted body.

It ships with a built-in local CORS proxy, so it works against APIs that do
**not** send CORS headers (like the Prestmit Partner API) directly from the
browser.

## One-command run

```bash
python3 cors_proxy.py
```

Then open <http://localhost:8787/> in your browser. The proxy serves the tester
UI at `/`, and the tester's proxy requests go back to the same origin
(`/?url=<target>`) — so there is **no CORS preflight at all**. Enable the
**CORS / Proxy** toggle in the app (Local proxy is pre-selected) and press
**Send**.

Custom port:

```bash
python3 cors_proxy.py 9000
```

## Files

| File | Purpose |
| --- | --- |
| `api-tester.html` | The tester UI — single self-contained HTML file (inline CSS + JS, no build step). Can also be opened directly via `file://`. |
| `cors_proxy.py` | Zero-dependency (Python stdlib) local CORS proxy. Serves the UI at `/` and forwards browser requests to any target at `/?url=<encoded target>`. |

No `requirements.txt` — only the Python 3 standard library is used.

## Features

- **Method** selector: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS` (color-coded).
- **URL** + **query-params** editor that builds the query string.
- **Auth** presets that add the right header automatically:
  - *API Key* — custom header name (e.g. `API-KEY`) + value
  - *Bearer token*
  - *Basic auth* (user / password)
  - *None*
- **Headers** editor (add / remove rows) layered on top of Auth.
- **Body** editor with live JSON validation (used for `POST` / `PUT` / `PATCH`).
- **Environment** swap — Prestmit Sandbox ↔ Live rewrites the host prefix.
- **Response panel:** colored status badge + status text, response time, size,
  a response-headers table, and pretty-printed JSON with syntax highlighting.
  Tabs: **Body** / **Headers** / **cURL**.
- **Copy as cURL** — generates the equivalent cURL command so you can run a
  request in a terminal even if the browser blocks it.
- **History** — the last 30 requests are saved in `localStorage`; click to reload.

## Example: Prestmit "Fetch Buyable Gift Cards"

1. `python3 cors_proxy.py` and open <http://localhost:8787/>.
2. Click **Load example** (top bar). This fills in:
   - Method: `GET`
   - URL: `https://dev-api.prestmit.io/partners/v1/giftcard-trade/buy/fetch-buyable-giftcards`
   - Auth: *API Key*, header `API-KEY`, value `key_dev_…` (sandbox key)
   - Params: `perPage=10`, `page=1`
   - Header: `Accept: application/json`
3. Enable the **CORS / Proxy** toggle (Local proxy pre-selected).
4. **Send** → you get a `200 OK` with the paginated gift-card JSON.

> A `key_dev_…` sandbox key only works against `dev-api.prestmit.io`; a live key
> only against `api.prestmit.io`. Use the **Environment** chips to swap.

## Why a proxy is needed

Browsers enforce CORS. Most APIs (Prestmit included) do not send
`Access-Control-Allow-Origin`, so a direct browser `fetch` to them is blocked.
The local proxy in this repo forwards your request verbatim — including custom
headers like `API-KEY` — and returns the response with
`Access-Control-Allow-Origin: *`, so the browser can read it.

Two public third-party proxies (`corsproxy.io`, `allorigins.win`) are also
listed in the app, but **they are not recommended for authenticated calls** —
they typically strip custom request headers, so authenticated APIs return
`401` through them.

## Security notes

- The proxy binds to `127.0.0.1` only — it is reachable solely from your machine.
- It logs each forwarded request line (method + path) but **never** logs header
  values or request bodies.
- Your API key is forwarded only to the exact target URL you enter.
- For sensitive keys, prefer running this local proxy over any third-party proxy.

## Tested against

Prestmit Partner API — `GET /giftcard-trade/buy/fetch-buyable-giftcards` on the
sandbox host, with 13 checks covering auth, pagination (`page` / `perPage`),
the `currencyCode` filter, and response-schema conformance. See the
`download/prestmit_api_test_report.md` artifact in the originating workspace for
the full report.
