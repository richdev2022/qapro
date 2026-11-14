// api/proxy.mjs — Vercel serverless function that forwards a request to an
// arbitrary target URL and returns the response with CORS headers, so the
// API Tester UI (served as static index.html at /) can reach APIs that do not
// themselves send Access-Control-Allow-Origin (e.g. the Prestmit Partner API).
//
// Contract (same as the local cors_proxy.py):
//     GET/POST/... /api/proxy?url=<URL-encoded target URL>
// The method, headers and body of the incoming request are forwarded to the
// target verbatim (custom headers like API-KEY included), and the target's
// status, headers and body are relayed back with Access-Control-Allow-Origin: *.
//
// Uses only the global `fetch` (Node 18+, which Vercel provides) — no deps.

const DROP_REQ = new Set([
  "host", "content-length", "connection", "keep-alive", "transfer-encoding",
  "upgrade", "accept-encoding", "origin", "referer",
]);
const DROP_RESP = new Set([
  "content-encoding", "content-length", "transfer-encoding", "connection",
  "keep-alive", "upgrade",
]);
const METHODS_WITH_BODY = new Set(["POST", "PUT", "PATCH", "DELETE"]);

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS",
  "Access-Control-Allow-Headers": "*",
  "Access-Control-Expose-Headers": "*",
  "Access-Control-Max-Age": "86400",
};

function corsHeaders(extra) {
  const h = new Headers(CORS);
  if (extra) for (const [k, v] of Object.entries(extra)) h.set(k, v);
  return h;
}

export default {
  async fetch(request) {
    // CORS preflight.
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    const target = new URL(request.url).searchParams.get("url");
    if (!target) {
      return new Response(
        JSON.stringify({ error: "Missing ?url=<target> query parameter." }),
        { status: 400, headers: corsHeaders({ "Content-Type": ["application/json"] }) }
      );
    }

    // Build the forwarded headers: copy everything except hop-by-hop / proxy /
    // encoding headers that the platform injects or that fetch recomputes.
    const fwdHeaders = new Headers();
    for (const [k, v] of request.headers.entries()) {
      const lk = k.toLowerCase();
      if (DROP_REQ.has(lk)) continue;
      if (lk.startsWith("x-vercel") || lk.startsWith("x-forwarded")) continue;
      fwdHeaders.set(k, v);
    }

    const init = { method: request.method, headers: fwdHeaders, redirect: "follow" };
    if (METHODS_WITH_BODY.has(request.method) && request.body) {
      // Forward the raw body bytes unchanged.
      init.body = await request.arrayBuffer();
    }

    let upstream;
    try {
      upstream = await fetch(target, init);
    } catch (err) {
      return new Response(
        JSON.stringify({
          error: "Upstream request failed.",
          detail: String((err && err.message) || err),
          target,
        }),
        { status: 502, headers: corsHeaders({ "Content-Type": ["application/json"] }) }
      );
    }

    // Relay upstream status + headers + body. Strip encoding/length headers
    // because fetch already decompressed the body and recomputes the length.
    const outHeaders = corsHeaders();
    for (const [k, v] of upstream.headers.entries()) {
      if (DROP_RESP.has(k.toLowerCase())) continue;
      outHeaders.set(k, v);
    }
    const buf = Buffer.from(await upstream.arrayBuffer());
    return new Response(buf, { status: upstream.status, headers: outHeaders });
  },
};
