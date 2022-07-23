import asyncio

from pygelbooru import Gelbooru

from app.models import Image, Link
from app.telegraph import Telegraph
from config import *


async def search_posts(tags: str, begin=0, end=1):
    if not tags:
        return

    gelbooru = Gelbooru(api_key, user_id)

    for page in range(begin, end):
        data = await gelbooru.search_posts(tags=tags.split(' '), page=page, limit=100)

        if not data:
            break

        yield data, page


async def main():
    tags = ''
    title = ''
    begin = 0
    end = 100
    max_coro = 20

    async with Telegraph(token=token, proxy=proxy, max_coro=max_coro) as ph:
        await ph.create_account(author_name)

        # latest_page = None

        async for posts, page in search_posts(tags, begin, end):
            print(f'crawing page: {page + 1}/{end}')

            file_urls = [item.file_url for item in posts]
            content = [Image(src=url) for url in await ph.upload_files(file_urls)]

            content.append(Link(href='https://www.baidu.com'))

            _title = f'{title or tags} {page + 1}'
            result = await ph.create_page(_title, author_name, content, author_url=author_url)

            print(result['result']['url'])

if __name__ == '__main__':
    asyncio.run(main())
