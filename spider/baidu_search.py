# -*- coding: utf-8 -*-
# @Time    :   2025/03/24 18:22:05
# @Author  :   lixumin1030@gmail.com
# @FileName:   baidu_search.py


import time
import requests
import asyncio
import aiohttp, aiofiles
import os
import re
import json
import logging
from aiohttp import ClientTimeout
from spider.user_agent import UserAgent
from utils.token_helper import get_acs_token_async


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
        
        # Token caching
        self._acs_token = None
        self._token_timestamp = 0
        self._token_expiry = 1800  # 30 minutes

    async def _get_valid_token(self, force_refresh=False):
        """Get a valid acs-token, refreshing if necessary."""
        try:
            # Pass force_refresh to the helper
            token = await get_acs_token_async(force_refresh=force_refresh)
            if token:
                logger.info(f"Successfully obtained acs-token: {token[:20]}...")
            else:
                logger.error("Failed to obtain acs-token")
            return token
        except Exception as e:
            logger.error(f"Error obtaining acs-token: {e}")
            return None

    async def search_image(
        self,
        image_bytes: bytes, 
        headers: dict
    ) -> str:
        # Initial token fetch (tries disk first)
        token = await self._get_valid_token(force_refresh=False)
        if token:
            headers["acs-token"] = token
            
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
                    
                    # 添加 uptime 参数
                    uptime = int(time.time() * 1000)
                    upload_url = f"{self.upload_image_api}?uptime={uptime}"

                    async with session.post(upload_url, headers=headers, data=form, ssl=False, timeout=timeout) as response:
                        # Handle text response first to check for errors
                        # text = await response.text()
                        # print(text) 
                        # Only print text if error occurs or for debug
                        
                        if response.status == 200:
                            try:
                                resp_data = await response.json()
                            except Exception:
                                # Not JSON, might be an error page
                                text = await response.text()
                                logger.error(f"Response is not JSON: {text[:200]}")
                                # Check if it's a token error (heuristic)
                                # If we haven't retried with a new token yet, try once
                                if "为了保障您的账号安全" in text or "验证码" in text: # Example error messages
                                     # Force refresh token and retry
                                     logger.warning("Token might be invalid, refreshing...")
                                     token = await self._get_valid_token(force_refresh=True)
                                     if token:
                                         headers["acs-token"] = token

                                return ""

                            if "data" in resp_data and "url" in resp_data["data"]:
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
                                logger.warning("Received 403, token likely expired. Refreshing token...")
                                token = await self._get_valid_token(force_refresh=True)
                                if token:
                                    headers["acs-token"] = token
                                    # Continue retries
                                
                                retries += 1
                                if retries < self.upload_max_retries:
                                    await asyncio.sleep(2 ** retries) # Exponential backoff
                                else:
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
    with open("./test_image/1.png", "rb") as f:
        image_bytes = f.read()

    search_url = asyncio.run(spider(image_bytes=image_bytes))
    # print(search_url)