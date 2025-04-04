# -*- coding: utf-8 -*-
# @Time    :   2025/03/24 18:22:05
# @Author  :   lixumin1030@gmail.com
# @FileName:   baidu_search.py


import requests
import asyncio
import aiohttp, aiofiles
import os
import re
import json
import logging
from aiohttp import ClientTimeout
from .user_agent import UserAgent


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class BaiduSimilarImageSpider:
    def __init__(self):
        self.max_page_size = 300
        self.upload_timeout = 60
        self.upload_connect_timeout = 10
        self.upload_sock_connect_timeout = 20
        self.upload_sock_read_timeout = 20
        self.upload_max_retries = 4

        self.upload_image_api = "https://graph.baidu.com/upload"


    async def search_image(
        self,
        image_bytes: bytes, 
        headers: dict
    ) -> str:
        async with aiohttp.ClientSession() as session:
            logger.info(f"开始上传图像, 图像文件内容大小: {len(image_bytes)} bytes")

            timeout = ClientTimeout(
                    total=self.upload_timeout,  # 设置整个请求的超时
                    connect=self.upload_connect_timeout,  # 设置连接的超时
                    sock_connect=self.upload_sock_connect_timeout,  # 设置套接字连接超时
                    sock_read=self.upload_sock_read_timeout  # 设置读取数据的超时
            )
            retries = 0
            while retries < self.upload_max_retries:
                try:
                    form = aiohttp.FormData()
                    form.add_field('image', image_bytes, filename='image.jpg', content_type='image/jpeg')

                    async with session.post(self.upload_image_api, headers=headers, data=form, ssl=False, timeout=timeout) as response:
                        text = await response.text()
                        if response.status == 200:
                            resp_data = await response.json()
                            search_url_base = resp_data["data"]["url"]
                            # 提取session_id和sign，处理search返回为None的情况
                            session_match = re.search(r'session_id=([0-9]+)', search_url_base)
                            sign_match = re.search(r'sign=([a-fA-F0-9]+)', search_url_base)
                            
                            if not session_match or not sign_match:
                                logger.error("无法从URL中提取session_id或sign")
                                return ""
                                
                            session_id = session_match.group(1)
                            sign = sign_match.group(1)

                            search_url = f"https://graph.baidu.com/ajax/similardetailnew?card_key=common&carousel=1&contsign=&curAlbum=0&entrance=GENERAL&f=general&image=&index=0&inspire=common&jumpIndex=&next=2&pageFrom=graph_upload_wise&page_size={self.max_page_size}&render_type=card_all&session_id={session_id}&sign={sign}&srcp=&wd=&page=1"
                            logger.info(f"图像上传成功，URL: {search_url}")
                            return search_url
                        else:
                            logger.error(f"图像上传失败，状态码: {response.status}")
                            if 403 == response.status:
                                retries += 1
                                logger.error(f"被流控，上传失败, 重试 {retries}/{self.upload_max_retries}")
                                if retries < self.upload_max_retries:
                                    await asyncio.sleep(5 ** retries)  # 指数退避
                                else:
                                    logger.error(f"已达到最大重试次数，放弃上传")
                                    return ""
                            else:
                                return ""

                except aiohttp.ClientError as e:
                    retries += 1
                    logger.error(f"网络错误，无法上传图像, 错误信息: {str(e)} - 重试 {retries}/{self.upload_max_retries}")
                    if retries < self.upload_max_retries:
                        await asyncio.sleep(2 ** retries)  # 指数退避
                    else:
                        logger.error(f"已达到最大重试次数，放弃上传")
                        return ""
                
                except Exception as e:
                    logger.error(f"上传图像时出错, 错误信息: {str(e)}")
                    return ""
    
    async def __call__(self, image_bytes: bytes, proxy=None) -> str:
        user_agent = UserAgent()
        headers = {"User-Agent": user_agent()}

        search_url = await self.search_image(image_bytes, headers)
        logger.info(f"请求search_url并整理相似图片url: {search_url}")
        search_images_url = await self.postprocess(search_url)
        logger.info(f"获取相似图片成功，demo:{search_images_url[0]}")
        
        return search_url

    async def postprocess(self, search_url):
        async with aiohttp.ClientSession() as session:
             async with session.get(search_url) as response:
                search_data = await response.json()
                images_url = [item["thumbUrl"] for item in search_data["data"]["list"]]
                return images_url


if __name__ == "__main__":
    spider = BaiduSimilarImageSpider()
    with open("../test_image/1.png", "rb") as f:
        image_bytes = f.read()

    search_url = asyncio.run(spider(image_bytes=image_bytes))
    # print(search_url)