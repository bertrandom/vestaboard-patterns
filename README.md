uv run prisma generate

uv run prisma db push

Dump:

sqlite-utils data/patterns.db "SELECT * from Message" > data/seed/message.json
sqlite-utils data/patterns.db "SELECT * from Pick" > data/seed/pick.json

Load:

sqlite-utils insert data/patterns.db Message data/seed/message.json
sqlite-utils insert data/patterns.db Pick data/seed/pick.json