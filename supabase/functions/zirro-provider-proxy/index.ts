// Supabase Edge Function: keeps provider API keys server-side.
// Configure these Supabase Edge Function secrets:
// FAL_KEY, KIE_AI_API_KEY, GROQ_API_KEY, ZIRRO_SUPABASE_PROXY_TOKEN
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-zirro-proxy-token",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ error: "POST only" }, 405);

  const expected = Deno.env.get("ZIRRO_SUPABASE_PROXY_TOKEN") || "";
  const supplied = req.headers.get("x-zirro-proxy-token") || "";
  if (!expected || !supplied || supplied !== expected) {
    return json({ error: "Unauthorized proxy request" }, 401);
  }

  let input: any;
  try { input = await req.json(); } catch { return json({ error: "Invalid JSON body" }, 400); }
  const provider = String(input.provider || "").toLowerCase();
  const method = String(input.method || "POST").toUpperCase();
  const path = String(input.path || "");
  if (!["GET", "POST"].includes(method)) return json({ error: "Only GET and POST are supported" }, 400);
  if (!path || path.length > 500 || path.includes("..") || path.includes("://") ||
      path.includes("\\\\") || path.includes("#")) {
    return json({ error: "Invalid provider path" }, 400);
  }
  const queryAt = path.indexOf("?");
  const routePath = queryAt >= 0 ? path.slice(0, queryAt) : path;
  const queryString = queryAt >= 0 ? path.slice(queryAt + 1) : "";
  if (queryString && !/^[a-zA-Z0-9._~%=&-]+$/.test(queryString)) {
    return json({ error: "Invalid provider query string" }, 400);
  }

  let base = "";  let base = "";
  let secretName = "";
  let authScheme = "Bearer";
  if (provider === "groq") {
    base = "https://api.groq.com/openai/v1";
    secretName = "GROQ_API_KEY";
    if (!["/chat/completions", "/models"].includes(path)) return json({ error: "Groq path not allowed" }, 400);
  } else if (provider === "fal") {
    base = "https://queue.fal.run";
    secretName = "FAL_KEY";
    authScheme = "Key";
    if (!/^\/[a-zA-Z0-9._/-]+$/.test(routePath) || !routePath.startsWith("/fal-ai/"))
      return json({ error: "Only fal-ai model routes are allowed" }, 400);
  } else if (provider === "kie") {
    base = "https://api.kie.ai";
    secretName = "KIE_AI_API_KEY";
    if (!routePath.startsWith("/api/v1/") || !/^\/[a-zA-Z0-9._/-]+$/.test(routePath))
      return json({ error: "Only Kie AI /api/v1 routes are allowed" }, 400);
  } else {
    return json({ error: "Provider must be groq, fal, or kie" }, 400);
  }

  const key = Deno.env.get(secretName) || "";
  if (!key) return json({ error: "Missing Supabase Edge Function secret: " + secretName }, 503);

  const headers = new Headers({ "Authorization": authScheme + " " + key, "Accept": "application/json" });
  let body: string | undefined;
  if (method === "POST") {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(input.body ?? {});
  }
  try {
    const target = base + routePath + (queryString ? "?" + queryString : "");
    const upstream = await fetch(target, { method, headers, body, signal: AbortSignal.timeout(110000) });
    const text = await upstream.text();
    return new Response(text, {
      status: upstream.status,
      headers: { ...corsHeaders, "Content-Type": upstream.headers.get("content-type") || "application/json", "Cache-Control": "no-store" },
    });
  } catch (_error) {
    return json({ error: "Provider request failed. Check the provider key, model route, and account access." }, 502);
  }
});

function json(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}
