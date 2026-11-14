# QA Pro — API Tester

A small, dependency-free visual API tester. Pick a method, enter a URL, set
your headers / auth / body, hit **Send**, and see the raw JSON response —
status, timing, size, response headers, and a syntax-highlighted body.

It ships with a built-in CORS proxy (both as a Vercel serverless function and a
local Python script), so it works against APIs that do **not** send CORS headers
(like the Prestmit Partner API) directly from the browser.

> This is **not** a React/Next.js app — it is a single self-contained HTML file
> (`index.html`) plus a tiny proxy. There is no build step.

## Deploy to Vercel (recommended)

1. Push this repo to GitHub (it already lives at
   `richdev2022/qapro`).
2. In Vercel, **New Project → Import** the repo. Vercel auto-detects:
   - `index.html` → served as the static UI at `/`
   - `api/proxy.mjs` → a serverless function at `/api/proxy`
3. Deploy (no environment variables, no build command needed).
4. Open the deployment URL. Click **Load example**, then **Send**.

The app auto-enables the **Same-origin** proxy preset when opened over
`http`/`https`, so requests to `/api/proxy?url=<target>` are same-origin
(no CORS preflight) and the serverless function forwards your headers —
including `API-KEY` — intact to the target.

## Run locally

```bash
python3 cors_proxy.py        # serves UI + proxy on http://localhost:8787
python3 cors_proxy.py 9000   # custom port
```

Open <http://localhost:8787/>. The proxy serves the UI at `/` and also answers
`/api/proxy?url=<target>` (same contract as the deployed function), so the
**Same-origin** preset works identically to the Vercel deployment.

Opening `index.html` directly via `file://` also works for the UI, but the
proxy must then be reached at an absolute URL — run `cors_proxy.py` and pick the
**Local proxy (file://)** preset.

## Files

| File | Purpose |
| --- | --- |
| `index.html` | The tester UI — single self-contained HTML file (inline CSS + JS, no build step). Served at `/` by Vercel and by the local proxy. |
| `api/proxy.mjs` | Vercel serverless function (Node, Web-standard `fetch` handler, no deps). Forwards `/api/proxy?url=<target>` to the target with method/headers/body intact, returns the response with CORS headers. |
| `cors_proxy.py` | Zero-dependency (Python stdlib) local CORS proxy. Serves the UI at `/` and forwards `?url=<target>` requests — the local counterpart of `api/proxy.mjs`. |
| `vercel.json` | Sets the function `maxDuration` (30s) and memory. |

No `requirements.txt`, no `package.json` — only the Python 3 stdlib and Node's
built-in `fetch` are used.

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

1. Open the deployed URL (or `http://localhost:8787/` locally).
2. Click **Load example** (top bar). This fills in:
   - Method: `GET`
   - URL: `https://dev-api.prestmit.io/partners/v1/giftcard-trade/buy/fetch-buyable-giftcards`
   - Auth: *API Key*, header `API-KEY`, value `key_dev_…` (sandbox key)
   - Params: `perPage=10`, `page=1`
   - Header: `Accept: application/json`
3. The **CORS / Proxy** toggle is auto-enabled (Same-origin preset). Press **Send**
   → you get a `200 OK` with the paginated gift-card JSON.

> A `key_dev_…` sandbox key only works against `dev-api.prestmit.io`; a live key
> only against `api.prestmit.io`. Use the **Environment** chips to swap.

## Why a proxy is needed

Browsers enforce CORS. Most APIs (Prestmit included) do not send
`Access-Control-Allow-Origin`, so a direct browser `fetch` to them is blocked.
The proxy forwards your request verbatim — including custom headers like
`API-KEY` — and returns the response with `Access-Control-Allow-Origin: *`, so
the browser can read it.

Two public third-party proxies (`corsproxy.io`, `allorigins.win`) are also listed
in the app, but **they are not recommended for authenticated calls** — they
typically strip custom request headers, so authenticated APIs return `401`
through them.

## Security notes

- The local proxy binds to `127.0.0.1` only — reachable solely from your machine.
- The Vercel function is public (anyone with the URL can use it as a CORS proxy),
  but forwards your headers only to the exact target URL you specify and never
  logs header values or request bodies.
- For sensitive keys, prefer the local proxy or a privately-deployed copy of the
  Vercel function over any third-party proxy.
