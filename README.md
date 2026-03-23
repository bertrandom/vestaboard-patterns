ENV=dev uv run main.py

## Vestaboard Pattern DB
0 7 * * * cd /web/vestaboard-patterns && ENV=prod /home/bertrand/.local/bin/uv run main.py >> /dev/null 2>&1

uv run prisma generate

uv run prisma db push

Dump:

sqlite-utils data/patterns.db "SELECT * from Message" > data/seed/message.json
sqlite-utils data/patterns.db "SELECT * from Pick" > data/seed/pick.json

Load:

sqlite-utils insert data/patterns.db Message data/seed/message.json
sqlite-utils insert data/patterns.db Pick data/seed/pick.json