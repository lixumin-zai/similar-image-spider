# -*- coding: utf-8 -*-
# @Time    :   2025/03/24 18:22:22
# @Author  :   lixumin1030@gmail.com
# @FileName:   main.py


import requests
import asyncio
import aiohttp, aiofiles
import os
import re
import json
import logging
from aiohttp import ClientTimeout

from spider import BaiduSimilarImageSpider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    spider = BaiduSimilarImageSpider()
    logger.info("123")
    with open("./test_image/1.jpg", "rb") as f:
        image_bytes = f.read()

    search_url = asyncio.run(spider(image_bytes=image_bytes))
    
    


