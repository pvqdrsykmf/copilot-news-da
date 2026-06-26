#!/usr/bin/env bash
# Smoke test dell'API /api/flags contro un deploy (preview o prod).
# uso: BASE=https://<deploy>.pages.dev tools/test_flags_api.sh
set -euo pipefail
BASE="${BASE:?Imposta BASE=<url del deploy>}"
ID="smoke-$(date +%s)"

echo "1) GET shape"
curl -fsS "$BASE/api/flags" | python3 -c "import sys,json;d=json.load(sys.stdin);assert 'news' in d and 'prompts' in d;print('  ok shape')"

echo "2) POST set (prompt)"
curl -fsS -X POST "$BASE/api/flags" -H 'content-type: application/json' \
  -d "{\"type\":\"prompt\",\"id\":\"$ID\",\"action\":\"set\"}" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);assert '$ID' in d['prompts'];print('  ok set')"

echo "3) POST unset"
curl -fsS -X POST "$BASE/api/flags" -H 'content-type: application/json' \
  -d "{\"type\":\"prompt\",\"id\":\"$ID\",\"action\":\"unset\"}" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);assert '$ID' not in d['prompts'];print('  ok unset')"

echo "4) POST invalido -> 400"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/api/flags" -H 'content-type: application/json' -d '{"type":"x"}')
test "$code" = "400" && echo "  ok 400" || { echo "  atteso 400, ottenuto $code"; exit 1; }
echo "TUTTI OK"
