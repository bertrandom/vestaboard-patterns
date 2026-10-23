#!/bin/bash
set -e

rsync -av \
  --include='/config/prod.json5' \
  --include='**/.gitignore' \
  --exclude='/.git' \
  --filter=':- .gitignore' \
  --delete-after \
  ./ bertrand@server:/web/vestaboard-patterns/

# Install dependencies, then regenerate the Prisma client (it lives in .venv,
# so any reinstall of the prisma package wipes it)
ssh bertrand@server 'cd /web/vestaboard-patterns &&
  ~/.local/bin/uv sync --locked --managed-python &&
  ~/.local/bin/uv run prisma generate'
