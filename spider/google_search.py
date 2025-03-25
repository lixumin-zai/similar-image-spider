# -*- coding: utf-8 -*-
# @Time    :   2025/03/24 18:21:55
# @Author  :   lixumin1030@gmail.com
# @FileName:   google_search.py


import io
import re
import random
import requests
import asyncio
import aiohttp, aiofiles
import json
import logging
from user_agent import UserAgent


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class GoogleSimilarImageSpider:
    def __init__(self):
        self.max_page_size = 300
        self.upload_timeout = 60
        self.upload_connect_timeout = 10
        self.upload_sock_connect_timeout = 20
        self.upload_sock_read_timeout = 20
        self.upload_max_retries = 4

        self.upload_image_api = "https://lens.google.com/upload?hl="

    async def __call__(self, image_bytes: bytes, lang: str="zh-CN") -> str:
        user_agent = UserAgent()
        headers = {"User-agent": user_agent()}
        async with aiohttp.ClientSession() as session:
            session.headers.update(headers)
            form = aiohttp.FormData()
            form.add_field(
                'encoded_image', 
                open("/root/project/baidu_spider/baidu-image-search/test_image/2.png", "rb"), 
                filename='image.png', 
                content_type='image/png'
            )
            # aiohttp.ClientSession().post(url=self.upload_image_api + lang)
            async with session.post(self.upload_image_api + lang, headers=headers, data=form, allow_redirects=False, proxy="http://localhost:7890") as response:
                print(response)
        return search_url


if __name__ == "__main__":
    spider = GoogleSimilarImageSpider()
    with open("/root/project/baidu_spider/baidu-image-search/test_image/2.png", 'rb') as imageFile:
        image_bytes = imageFile.read()
        asyncio.run(spider(image_bytes))