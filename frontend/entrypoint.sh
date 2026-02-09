#!/bin/sh
set -e

PLACEHOLDER="__NEXT_PUBLIC_API_URL_PLACEHOLDER__"
API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"

# Replace placeholder in all built JS files with the runtime value.
# Uses '|' as sed delimiter since URLs contain '/'.
find /app/.next -name "*.js" -exec sed -i "s|${PLACEHOLDER}|${API_URL}|g" {} +
find /app -maxdepth 1 -name "server.js" -exec sed -i "s|${PLACEHOLDER}|${API_URL}|g" {} +

exec node server.js
