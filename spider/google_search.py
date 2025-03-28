# -*- coding: utf-8 -*-
# @Time    :   2025/03/24 18:21:55
# @Author  :   lixumin1030@gmail.com
# @FileName:   google_search.py


import io
import re
import random
import requests
import asyncio
import aiohttp
import json
import logging
import time  # 添加time模块
from bs4 import BeautifulSoup
from user_agent import UserAgent
from PIL import Image

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
        self.proxy = "http://localhost:7890"

        # 需要手动设置cookie
        self.cookie = ""


    async def __call__(self, image_bytes: bytes, lang: str="zh-CN") -> dict:
        """
        使用Google Lens搜索相似图片
        
        Args:
            image_bytes: 图片二进制数据
            lang: 语言设置
            
        Returns:
            dict: 包含搜索结果的字典
        """
        try:
            # 第一步：上传图片获取重定向URL
            redirect_url = await self._upload_image(image_bytes, lang)
            if not redirect_url:
                logger.error("获取重定向URL失败")
                return {"success": False, "message": "获取重定向URL失败"}
            
            # 第二步：获取搜索结果页面
            search_results = await self._get_search_results(redirect_url)
            
            return search_results
        except Exception as e:
            logger.error(f"Google Lens搜索失败: {str(e)}")
            return {"success": False, "message": f"搜索失败: {str(e)}"}

    async def _upload_image(self, image_bytes: bytes, lang: str) -> str:
        """上传图片到Google Lens并获取重定向URL"""
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        headers = {    
            'Cookie': self.cookie,
            'User-Agent': user_agent
        }
        # 获取图片尺寸
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = image.size

        with io.BytesIO() as output:
            image.save(output, format="PNG", optimize=True)
            image_bytes = output.getvalue()
        
        # 生成随机文件名
        random_filename = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=8))
        file_name = f"{random_filename}.png"
        
        # 更新上传API地址，包含更多参数
        current_time = int(time.time() * 1000)
        params = {
            'hl': lang,
            'ep': 'ccm',
            're': 'dcsp',
            's': '4',
            'st': str(current_time),
            'sideimagesearch': '1',
            'vpw': str(w),
            'vph': str(h)
        }
        # upload_url = f"https://lens.google.com/v3/upload?hl={lang}&st={current_time}&ep=gisbubb&vpw={w}&vph={h}"
        upload_url = "https://lens.google.com/upload"
        async with aiohttp.ClientSession() as session:
            # 使用multipart/form-data格式上传图片
            form = aiohttp.FormData()
            form.add_field(
                'encoded_image', 
                io.BytesIO(image_bytes), 
                filename=file_name, 
                content_type='image/png'
            )
            form.add_field('original_width', str(w))
            form.add_field('original_height', str(h))
            form.add_field('processed_image_dimensions', f"{w},{h}")
            
            try:
                logger.info(f"正在上传图片到 {upload_url}")
                async with session.post(
                    upload_url, 
                    params=params,
                    headers=headers, 
                    data=form, 
                    allow_redirects=False, 
                    proxy=self.proxy,
                    timeout=aiohttp.ClientTimeout(total=self.upload_timeout)
                ) as response:
                    logger.info(f"上传图片响应状态码: {response.status}")
                    if response.status in (301, 302, 303, 307, 308):
                        redirect_url = response.headers.get("Location", "")
                        print(response.headers)
                        logger.info(f"获取到重定向URL: {redirect_url}")
                        return redirect_url
                    else:
                        response_text = await response.text()
                        logger.error(f"上传图片失败，状态码: {response.status}, 响应内容: {response_text[:200]}...")
                        return ""
            except Exception as e:
                logger.error(f"上传图片异常: {str(e)}")
                return ""
    
    async def _get_search_results(self, redirect_url: str) -> dict:
        """获取Google Lens搜索结果"""
        user_agent = UserAgent()
        headers = {"User-agent": user_agent(), "cookie": self.cookie}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    redirect_url, 
                    headers=headers, 
                    proxy=self.proxy,
                    timeout=aiohttp.ClientTimeout(total=self.upload_timeout)
                ) as response:
                    logger.info(f"获取搜索结果响应状态码: {response.status}")
                    if response.status != 200:
                        return {"success": False, "message": f"获取搜索结果失败，状态码: {response.status}"}
                    
                    html_content = await response.text()
                    with open("test.html", "w", encoding="utf-8") as f:
                        f.write(html_content)
                    return {}
            except Exception as e:
                logger.error(f"获取搜索结果异常: {str(e)}")
                return {"success": False, "message": f"获取搜索结果异常: {str(e)}"}
    


if __name__ == "__main__":
    async def main():
        import os
        spider = GoogleSimilarImageSpider()
        image_path = "../test_image/2.png"
        
        # 检查文件是否存在
        if not os.path.exists(image_path):
            abs_path = os.path.abspath(image_path)
            print(f"错误: 图片文件不存在: {abs_path}")
            print(f"当前工作目录: {os.getcwd()}")
            return
            
        with open(image_path, 'rb') as imageFile:
            image_bytes = imageFile.read()
            if len(image_bytes) == 0:
                print("错误: 图片文件为空")
                return
                
            print(f"图片大小: {len(image_bytes)} 字节")
            results = await spider(image_bytes)
            print(json.dumps(results, ensure_ascii=False, indent=2))
    
    asyncio.run(main())