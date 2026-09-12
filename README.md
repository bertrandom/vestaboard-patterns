ENV=dev uv run main.py

## Vestaboard Pattern DB
0 7 * * * cd /web/vestaboard-patterns && ENV=prod /home/bertrand/.local/bin/uv run main.py >> /dev/null 2>&1

uv run prisma generate

uv run prisma db push

Dump:

uv run sqlite-utils data/patterns.db "SELECT * from Message" > data/seed/message.json
uv run sqlite-utils data/patterns.db "SELECT * from Pick" > data/seed/pick.json

Load:

uv run sqlite-utils insert data/patterns.db Message data/seed/message.json
uv run sqlite-utils insert data/patterns.db Pick data/seed/pick.json

Get a refresh token:

```
curl --url 'https://vestaboard.auth0.com/oauth/token' \
  -H 'accept: */*' \
  -H 'accept-language: en-US,en;q=0.9' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -H 'origin: https://web.vestaboard.com' \
  -H 'pragma: no-cache' \
  -H 'priority: u=1, i' \
  -H 'referer: https://web.vestaboard.com/' \
  -H 'sec-ch-ua: "Chromium";v="152", "Not?A_Brand";v="24", "Google Chrome";v="152"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: cross-site' \
  -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36' \
  --data-raw '{"client_id":"2h7PozmBi3wdH62adT1oIRdHwbcznzQc","grant_type":"http://auth0.com/oauth/grant-type/password-realm","username":"username@email.com","password":"password","audience":"https://vestaboard.auth0.com/api/v2/","scope":"offline_access openid profile email","realm":"Users"}'
  ```