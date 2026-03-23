import asyncio
import json
import logging
import logging.config
import os
import sys

import aiohttp
from appcfg import get_config
from prisma import Prisma

env = os.getenv("ENV", "dev").lower()

if env == "prod":
    logging.config.fileConfig('logging-prod.conf')
else:
    logging.config.fileConfig('logging.conf')

logger = logging.getLogger(__name__)

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        # let Ctrl+C behave normally
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical("Uncaught exception",
                    exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

GRAPH_URL = "https://api.vestaboard.com/graphql"
TOKEN_URL = "https://vestaboard.auth0.com/oauth/token"

config = get_config("main")

def get_graph_request_headers(token: str) -> dict:
    return {
        "x-vestaboard-token": token,
        "user-agent": "Vestaboard/804 CFNetwork/3860.400.51 Darwin/25.3.0",
        "content-type": "application/json",
    }


async def get_picks(token: str) -> list:
    payload = {
        "operationName": "ListInspiration",
        "variables": {
            "input": {
                "limit": 42,    # 3 messages per day, 14 days
                "cursor": None,
                "boardStyle": "black"
            }
        },
        "query": """query ListInspiration($input: ListInspirationInputV2!) {
  listInspirationV2(input: $input) {
    items {
      id
      pick {
        id
        date
        created
        attribution
        likeCount
        isLikedByMe
        mediumIcon: icon(size: Medium)
        message {
          id
          characters
          isFavorited
          __typename
        }
        __typename
      }
      feedItem {
        id
        created
        attribution
        likeCount
        isLikedByMe
        personId
        mediumIcon: icon(size: Medium)
        message {
          id
          characters
          isFavorited
          __typename
        }
        __typename
      }
      __typename
    }
    nextCursor
    __typename
  }
}"""
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            GRAPH_URL,
            headers=get_graph_request_headers(token),
            json=payload,
        ) as resp:
            resp.raise_for_status()
            body = await resp.json()

    items = body["data"]["listInspirationV2"]["items"]

    picks = []
    for item in items:
        picks.append(item["pick"])

    return picks

async def get_todays_picks(token: str) -> list:
    payload = {
        "operationName": "ListTodaysPicks",
        "variables": {
            "input": {
                "boardStyle": "black"
            }
        },
        "query": "query ListTodaysPicks($input: TodaysPicksInputV2) {\n  listTodaysPicks: listTodaysPicksV2(input: $input) {\n    picks {\n      id\n      attribution\n      created\n      date\n      likes\n      likeCount\n      isLikedByMe\n      mediumIcon: icon(size: Medium)\n      message {\n        id\n        characters\n        isFavorited\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            GRAPH_URL,
            headers=get_graph_request_headers(token),
            json=payload,
        ) as resp:
            resp.raise_for_status()
            body = await resp.json()

    picks = body["data"]["listTodaysPicks"]["picks"]

    return picks

async def get_access_token(refresh_token: str, client_id: str) -> str:
    payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            TOKEN_URL,
            data=payload,  # form-encoded
        ) as resp:
            resp.raise_for_status()
            body = await resp.json()

    return body["access_token"]

async def process_pick(db, item_pick) -> None:
    if not is_pattern(item_pick['message']['characters']):
        return

    message = await db.message.find_unique(
        where={
            'id': item_pick['message']['id']
        }
    )

    if message is None:
        message = await db.message.create(
            data={
                'id': item_pick['message']['id'],
                'body': json.dumps(item_pick['message']['characters'])
            },
        )

    pick = await db.pick.find_unique(
        where={
            'id': item_pick['id']
        }
    )

    if pick is None:
        pick = await db.pick.create(
            data={
                'id': item_pick['id'],
                'pick_date': item_pick['date'],
                'message_id': message.id
            },
        )

    logger.info(f"{pick.pick_date} - Pick: {pick.id}, Message: {message.id}")

def is_pattern(characters) -> bool:
    is_pattern = True
    for row in characters:
        for char in row:
            if (char >= 1 and char <= 36):
                is_pattern = False
    return is_pattern

async def main() -> None:

    if config["refresh_token"] == "xxx":
        logger.error("refresh token is not configured")
        return

    db = Prisma()
    await db.connect()

    # Enable WAL mode
    await db.query_raw(
        '''
        PRAGMA journal_mode = WAL;
        '''
    )

    access_token = await get_access_token(config["refresh_token"], config["client_id"])

    todays_picks = await get_todays_picks(access_token)
    for pick in todays_picks:
        await process_pick(db, pick)

    picks = await get_picks(access_token)

    for pick in picks:
        await process_pick(db, pick)

    await db.disconnect()

if __name__ == '__main__':
    asyncio.run(main())