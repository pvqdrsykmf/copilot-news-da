// Cloudflare Pages Function — stato condiviso flag (news + prompt). Route: /api/flags
// Binding KV richiesto: FLAGS
const KEYS = { news: "news_flags", prompt: "prompt_flags" };

export function applyFlag(doc, id, action, today) {
  const next = { ...(doc || {}) };
  if (action === "set") next[id] = { date: today };
  else if (action === "unset") delete next[id];
  return next;
}

function todayIT() {
  return new Date().toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit", year: "numeric" });
}

async function readState(env) {
  const [news, prompts] = await Promise.all([
    env.FLAGS.get(KEYS.news, "json"),
    env.FLAGS.get(KEYS.prompt, "json"),
  ]);
  return { news: news || {}, prompts: prompts || {} };
}

function jsonErr(msg, status) {
  return new Response(JSON.stringify({ error: msg }), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
}

export async function onRequestGet({ env }) {
  return Response.json(await readState(env), { headers: { "cache-control": "no-store" } });
}

export async function onRequestPost({ env, request }) {
  let body;
  try { body = await request.json(); } catch { return jsonErr("body non JSON", 400); }
  const { type, id, action } = body || {};
  if (!["news", "prompt"].includes(type)) return jsonErr("type non valido", 400);
  if (typeof id !== "string" || !id.trim()) return jsonErr("id mancante", 400);
  if (!["set", "unset"].includes(action)) return jsonErr("action non valida", 400);

  const key = KEYS[type];
  const current = (await env.FLAGS.get(key, "json")) || {};
  const updated = applyFlag(current, id, action, todayIT());
  await env.FLAGS.put(key, JSON.stringify(updated));
  return Response.json(await readState(env), { headers: { "cache-control": "no-store" } });
}
