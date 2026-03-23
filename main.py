import asyncio
import json

import aiohttp
from appcfg import get_config
from prisma import Prisma

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

    print(f"{pick.pick_date} - Pick: {pick.id}, Message: {message.id}")

def is_pattern(characters) -> bool:
    is_pattern = True
    for row in characters:
        for char in row:
            if (char >= 1 and char <= 36):
                is_pattern = False
    return is_pattern

async def main() -> None:
    db = Prisma()
    await db.connect()

    # Enable WAL mode
    await db.query_raw(
        '''
        PRAGMA journal_mode = WAL;
        '''
    )

    access_token = await get_access_token(config["refresh_token"], config["client_id"])

    picks = await get_picks(access_token)

    for pick in picks:
        await process_pick(db, pick)

    await db.disconnect()

if __name__ == '__main__':
    asyncio.run(main())