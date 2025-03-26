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
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": f"{lang},en-US;q=0.7,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Origin": "https://www.google.com",
            "Referer": "https://www.google.com/",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-User": "?1",
            "Sec-Ch-Ua": "\"Chromium\";v=\"134\", \"Not:A-Brand\";v=\"24\", \"Google Chrome\";v=\"134\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "macOS",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }
        image = Image.open(io.BytesIO(image_bytes))
        w, h = image.size
        # 更新上传API地址，包含更多参数
        current_time = int(time.time() * 1000)
        upload_url = f"https://lens.google.com/v3/upload?hl={lang}&st={current_time}&ep=gsbubb&vpw={w}&vph={h}"
        
        async with aiohttp.ClientSession() as session:
            # 使用multipart/form-data格式上传图片
            form = aiohttp.FormData()
            form.add_field(
                'encoded_image', 
                io.BytesIO(image_bytes), 
                filename='image.jpg', 
                content_type='image/jpeg'
            )
            
            try:
                logger.info(f"正在上传图片到 {upload_url}")
                async with session.post(
                    upload_url, 
                    headers=headers, 
                    data=form, 
                    allow_redirects=False, 
                    proxy=self.proxy,
                    timeout=aiohttp.ClientTimeout(total=self.upload_timeout)
                ) as response:
                    logger.info(f"上传图片响应状态码: {response.status}")
                    if response.status in (301, 302, 303, 307, 308):
                        redirect_url = response.headers.get("Location")
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
        headers = {"User-agent": user_agent()}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    redirect_url, 
                    headers=headers, 
                    proxy=self.proxy,
                    timeout=aiohttp.ClientTimeout(total=self.upload_timeout)
                ) as response:
                    if response.status != 200:
                        return {"success": False, "message": f"获取搜索结果失败，状态码: {response.status}"}
                    
                    html_content = await response.text()
                    return self._parse_search_results(html_content, redirect_url)
            except Exception as e:
                logger.error(f"获取搜索结果异常: {str(e)}")
                return {"success": False, "message": f"获取搜索结果异常: {str(e)}"}
    
    def _parse_search_results(self, html_content: str, url: str) -> dict:
        """解析Google Lens搜索结果页面"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 尝试提取JSON数据
            json_data = self._extract_json_data(html_content)
            
            # 提取视觉匹配结果
            visual_matches = []
            match_elements = soup.select('div[data-item-type="visuallysimilar"]')
            for element in match_elements:
                try:
                    img_element = element.select_one('img')
                    link_element = element.select_one('a')
                    if img_element and link_element:
                        visual_matches.append({
                            "image_url": img_element.get('src', ''),
                            "title": img_element.get('alt', ''),
                            "link": link_element.get('href', '')
                        })
                except Exception as e:
                    logger.warning(f"解析视觉匹配元素失败: {str(e)}")
            
            # 提取可能的文本识别结果
            ocr_text = ""
            ocr_element = soup.select_one('div[data-item-type="ocr"]')
            if ocr_element:
                ocr_text = ocr_element.get_text(strip=True)
            
            return {
                "success": True,
                "url": url,
                "visual_matches": visual_matches,
                "ocr_text": ocr_text,
                "json_data": json_data
            }
        except Exception as e:
            logger.error(f"解析搜索结果失败: {str(e)}")
            return {
                "success": False, 
                "message": f"解析搜索结果失败: {str(e)}",
                "url": url
            }
    
    def _extract_json_data(self, html_content: str) -> dict:
        """尝试从HTML中提取JSON数据"""
        try:
            # 尝试查找包含搜索结果的JSON数据
            json_match = re.search(r'AF_initDataCallback\(({.*?})\);', html_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                # 提取data字段
                data_match = re.search(r'"data":(\[.*?\])', json_str, re.DOTALL)
                if data_match:
                    data_str = data_match.group(1)
                    return json.loads(data_str)
            return {}
        except Exception as e:
            logger.warning(f"提取JSON数据失败: {str(e)}")
            return {}


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