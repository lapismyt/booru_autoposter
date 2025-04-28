import asyncio
from abc import ABC

import aiohttp
from rich import print
from yarl import URL

from models import GelbooruSearchResponse, DanbooruPost


class BooruAdapter(ABC):
    api_base: str = ...
    session: aiohttp.ClientSession

    def __init__(
            self,
            session: aiohttp.ClientSession | None = None,
            proxy: str | URL | None = None
        ):
        self.session = session or aiohttp.ClientSession(base_url=self.api_base, proxy=proxy)

    async def search(
            self,
            query: str,
            block: str | None = None,
            limit: int = 100,
            page: int = 0,
        ) -> dict:
        ...

    async def close(self):
        await self.session.close()


class GelbooruAdapter(BooruAdapter):
    api_base = 'https://gelbooru.com/'
    api_key: str | None = None
    user_id: str | None = None

    def __init__(
            self,
            session: aiohttp.ClientSession | None = None,
            proxy: str | URL | None = None,
            api_key: str | None = None,
            user_id: str | None = None
        ):
        super().__init__(session, proxy)
        self.api_key = api_key
        self.user_id = user_id

    async def search(
            self,
            query: str = '',
            limit: int = 100,
            page: int = 0,
            deleted: bool = False
    ) -> GelbooruSearchResponse:

        params = {
            'tags': query,
            'limit': limit,
            'pid': page,
            'json': 1
        }

        if self.api_key and self.user_id:
            params['api_key'] = self.api_key
            params['user_id'] = self.user_id

        if deleted: params['deleted'] = 'show'

        async with self.session.get(
                'index.php?page=dapi&s=post&q=index',
                params=params
            ) as resp:
            # print(await resp.json())
            return GelbooruSearchResponse.from_dict(await resp.json())


class DanbooruError(Exception):
    pass


class DanbooruAdapter(BooruAdapter):
    api_base = 'https://danbooru.donmai.us/'
    api_key: str | None = None
    username: str | None = None

    def __init__(
            self,
            session: aiohttp.ClientSession | None = None,
            proxy: str | URL | None = None,
            api_key: str | None = None,
            username: str | None = None
    ):
        super().__init__(session, proxy)
        self.api_key = api_key
        self.username = username

    async def search(
            self,
            query: str = '',
            limit: int = 100,
            page: int = 0,
            random: bool = False,
            md5: str = None
    ) -> list[DanbooruPost]:

        params = {
            'tags': query,
            'limit': limit,
            'page': page,
            'json': 1
        }

        if md5: params['md5'] = md5

        async with self.session.get(
                'posts.json',
                params=params
            ) as resp:
            conv: list | dict = await resp.json()
            if isinstance(conv, list):
                print(conv)
                return [DanbooruPost.from_dict(post) for post in conv]
            raise DanbooruError(conv['message'])



adapters = [
    GelbooruAdapter,
    DanbooruAdapter
]


async def main():
    danbooru = DanbooruAdapter(proxy='http://127.0.0.1:2080')
    print(await danbooru.search('catgirl animated', limit=2, random=True))
    await danbooru.close()


if __name__ == '__main__':
    asyncio.run(main())