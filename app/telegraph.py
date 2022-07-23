import asyncio
import json
from typing import Dict, List, Optional, Union

from aiohttp import ClientSession
from tqdm.asyncio import tqdm_asyncio

from app.models import get_model_formatter

class TelegraphImage(object):
    def __init__(self, title, src) -> None:
        self.title = title
        self.src = src


class TelegraphAPI(object):
    def __init__(self) -> None:
        self.base_url = 'https://api.telegra.ph'

    def contact_api(self, method):
        return f'{self.base_url}/{method}'

    @property
    def create_account(self):
        return self.contact_api('createAccount')

    @property
    def create_page(self):
        return self.contact_api('createPage')

    @property
    def upload(self):
        # unoffical api
        return 'https://telegra.ph/upload'

    @property
    def page_list(self):
        return self.contact_api('getPageList')


class Telegraph(object):
    def __init__(self, token=None, proxy=None, session: Optional[ClientSession] = None, max_coro=5) -> None:
        self.proxy = proxy
        self.session = session or ClientSession()
        self.api = TelegraphAPI()
        self.access_token = token or None
        self.semphore = asyncio.Semaphore(max_coro)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.session.close()

    async def create_account(self, short_name, author_name='', author_url=''):
        if self.access_token:
            # print('Use existed token')
            return

        api = self.api.create_account

        response = await self.request('POST', api, data={
            'short_name': short_name,
            'author_name': author_name,
            'author_url': author_url
        })

        if response['ok']:
            self.access_token = response['result']['access_token']
        else:
            raise ValueError('Get token failed:', response)

        return response

    async def request(self, method: str, url: str, binfile=False, **kwargs):
        headers = {
            'origin': 'https://telegra.ph',
            "referrer": "https://telegra.ph",
        }

        if 'headers' not in kwargs:
            kwargs['headers'] = {}

        kwargs['headers'].update(headers)

        access_token = {'access_token': self.access_token}

        for key in ['params', 'data']:
            if key in kwargs:
                kwargs[key].update(access_token)

        async with self.session.request(method, url, proxy=self.proxy, **kwargs) as resp:
            headers = resp.headers

            if method.lower() == 'head':
                return headers

            ctype = headers.get('content-type', '')

            if binfile:
                return await resp.read()

            if ctype.startswith('application/json'):
                return await resp.json()
            elif ctype.startswith('text/html'):
                return await resp.text()
            else:
                return await resp.read()

    async def get_page_list(self, offset: int = 0, limit: int = 50):
        api = self.api.page_list

        return await self.request('GET', api, params={
            'offset': offset,
            'limit': limit
        })

    async def upload_files(self, file_or_url_list: List[Union[bytes, str]], **kwargs):
        api = self.api.upload
        tasks = []

        async def download_task(file_or_url):
            if isinstance(file_or_url, str):
                async with self.semphore:
                    # 下载前先判断文件大小，超过 5MB 上传会失败
                    headers = await self.request('HEAD', file_or_url)
                    filesize = int(headers.get(
                        'content-length', -1)) // 1024 // 1024

                    if filesize >= 5:
                        return

                    file = await self.request('GET', file_or_url, binfile=True, **kwargs)
            elif isinstance(file_or_url, bytes):
                file = file_or_url
            else:
                raise ValueError('File argument\'s type must be bytes or string')

            if (len(file) // 1024 // 1024) >= 5:
                return

            files = {'file': file}
            data = await self.request('POST', api, data=files, **kwargs)

            src = None

            if data:
                try:
                    src = data[0]['src']
                    # print('uploaded:', src)
                except Exception as e:
                    print('upload file falied', e, data)
            else:
                print('upload file falied', data)

            return src

        for file_or_url in file_or_url_list:
            task = asyncio.create_task(download_task(
                file_or_url))  # type: ignore

            tasks.append(task)

        results = list(filter(lambda src: src, await tqdm_asyncio.gather(*tasks, desc='uploaded count')))

        return results

    async def create_page(self, title: str, author: str, content: List[Dict], author_url=''):
        api = self.api.create_page

        formatters = {
            'image': get_model_formatter('image.json'),
            'link': get_model_formatter('link.json')
        }

        formatted_content = []

        for item in content:
            model_type = item.pop('type')
            c = formatters[model_type](**item)
            formatted_content.append(c)

        data = {
            'title': title,
            'author_name': author,
            'author_url': author_url,
            'content': json.dumps(formatted_content),
        }

        return await self.request('POST', api, data=data)

# model = self.read_model()
# content = []

# for image in images:
#     m = self.format_model(model, img_src=image.src,
#                             img_caption=image.title)

#     content.append(m)

# content_json = json.dumps(content)
