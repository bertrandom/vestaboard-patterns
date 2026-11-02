# vestaboard-patterns

Archives the pattern-only messages from Vestaboard's daily "Today's Picks" into a local SQLite database.

Every day Vestaboard publishes a few curated messages. Some of them are text and some are pure color patterns. This script pulls today's picks plus the last two weeks of the inspiration feed from the Vestaboard GraphQL API. It keeps the patterns and saves them, so the collection grows over time.

## How it works

1. Exchanges a stored Auth0 refresh token for an access token.
2. Fetches `listTodaysPicksV2` and the latest 42 items of `listInspirationV2` (3 picks a day × 14 days) from `https://api.vestaboard.com/graphql`.
3. Skips any message that contains a letter or digit (character codes 1–36). Only messages made of blanks, punctuation and color tiles count as patterns.
4. Upserts each pattern into `data/patterns.db`. A `Message` row holds the 6×22 character grid as JSON. A `Pick` row records the date it was featured. Only new rows are logged.

The database runs in WAL mode, so other processes can read it while the script writes.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- A Vestaboard account

## Setup

Install dependencies and generate the Prisma client:

```bash
uv sync
```

```bash
uv run prisma generate
```

Create the database from `schema.prisma`:

```bash
uv run prisma db push
```

Optionally, load the seed data, a snapshot of patterns collected so far:

```bash
uv run sqlite-utils insert data/patterns.db Message data/seed/message.json
```

```bash
uv run sqlite-utils insert data/patterns.db Pick data/seed/pick.json
```

## Configuration

Configuration is loaded with [appcfg](https://github.com/bertrandom/appcfg). `config/default.json5` holds the defaults. Environment-specific overrides go in `config/development.json5` and `config/prod.json5`, which are gitignored.

| Key             | Description                                        |
| --------------- | -------------------------------------------------- |
| `client_id`     | Auth0 client ID used to refresh the access token   |
| `refresh_token` | Auth0 refresh token for your Vestaboard account   |

The script exits early if `refresh_token` is still the placeholder `xxx`.

### Getting a refresh token

Log in with Vestaboard's Auth0 password realm and copy `refresh_token` from the response. Replace the username and password with your own:

```bash
curl --url 'https://vestaboard.auth0.com/oauth/token' \
  -H 'content-type: application/json' \
  -H 'origin: https://web.vestaboard.com' \
  -H 'referer: https://web.vestaboard.com/' \
  --data-raw '{"client_id":"2h7PozmBi3wdH62adT1oIRdHwbcznzQc","grant_type":"http://auth0.com/oauth/grant-type/password-realm","username":"username@email.com","password":"password","audience":"https://vestaboard.auth0.com/api/v2/","scope":"offline_access openid profile email","realm":"Users"}'
```

## Running

```bash
ENV=dev uv run main.py
```

`ENV` selects the config overrides and the logging setup: `logging.conf` for dev, `logging-prod.conf` for prod. It defaults to `dev`.

## Deployment

`deploy.sh` rsyncs the project to the server, including `config/prod.json5`. It then runs `uv sync --locked` and `prisma generate` there. The client has to be regenerated after every sync because it lives in `.venv`.

```bash
./deploy.sh
```

In production the script runs from cron every morning:

```cron
0 7 * * * cd /web/vestaboard-patterns && ENV=prod /home/bertrand/.local/bin/uv run main.py >> /dev/null 2>&1
```

## Database

`schema.prisma` defines two tables:

- **Message**: `id` and `body`, the character grid as a JSON array of 6 rows × 22 character codes.
- **Pick**: `id`, `pick_date` (`YYYY-MM-DD`, indexed) and `message_id`. A message can be picked more than once.

To refresh the seed snapshot from the live database:

```bash
uv run sqlite-utils data/patterns.db "SELECT * from Message" > data/seed/message.json
```

```bash
uv run sqlite-utils data/patterns.db "SELECT * from Pick" > data/seed/pick.json
```

## License

[MIT](LICENSE)
