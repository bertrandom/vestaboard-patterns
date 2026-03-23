#!/bin/bash
rsync -av \
  --include='/config/prod.json5' \
  --include='**/.gitignore' \
  --exclude='/.git' \
  --filter=':- .gitignore' \
  --delete-after \
  ./ bertrand@server:/web/vestaboard-patterns/