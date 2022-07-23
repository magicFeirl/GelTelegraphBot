import logging
import asyncclick as click

from pygelbooru import Gelbooru

from app.models import Image, Link
from app.telegraph import Telegraph
from config import *


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

async def search_posts(tags: str, begin=0, end=1, limit=100):
    if not tags:
        return

    gelbooru = Gelbooru(api_key, user_id)

    for page in range(begin, end):
        data = await gelbooru.search_posts(tags=tags.split(' '), page=page, limit=limit)

        if not data:
            break

        yield data, page


@click.command()
@click.option('-tags', help='Gelbooru tags that you want to upload to telegraph')
@click.option('-title', default=None, help='Telegraph article title')
@click.option('-begin', default=0, help='Uploading tags start page')
@click.option('-end', default=1, help='Uploading tags end page')
@click.option('-coro', default=20, help='Concurrent donwloading number')
@click.option('-limit', default=100, help='Total items that per page returns')
# @click.option('-faststart', default=False, help='Don\'t show comfirm information')
async def main(tags: str, title = None, begin = 0, end = 1, coro = 20, limit = 100):
    """Download images from Gelbooru and upload them to Telegraph.
    
    e.g.: python main.py -title Gelbooru -tags '1girl rating:general'
    """
    if not tags:
        title = tags

    logger.info(tags)
    
    coro = 20

    async with Telegraph(token=token, proxy=proxy, max_coro=coro) as ph:
        await ph.create_account(author_name)

        # latest_page = None

        async for posts, page in search_posts(tags, begin, end, limit):
            logger.info(f'Requesting page: {page + 1}')

            file_urls = [item.file_url for item in posts]
         
            content = [Image(src=url) for url in await ph.upload_files(file_urls)]

            # content.append(Link(href='https://www.baidu.com'))

            _title = f'{title or tags} {page + 1}'
            result = await ph.create_page(_title, author_name, content, author_url=author_url)

            article_url = result['result']['url']

            logger.info(f'Upload done, link:\n{article_url}')

if __name__ == '__main__':
    main(_anyio_backend='asyncio')
