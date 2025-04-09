# -*- coding: utf-8 -*-
# @Time    :   2025/03/24 18:22:22
# @Author  :   lixumin1030@gmail.com
# @FileName:   main.py


import asyncio
from math import log
import os
import random
import logging
import argparse
from pathlib import Path
from typing import List, Tuple
from weakref import proxy
import requests
import json

from spider.baidu_search import BaiduSimilarImageSpider
from download_image import download_images

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_proxy() -> str:
    """
    从API获取代理地址
    
    Returns:
        str: 代理地址，如果获取失败则返回空字符串
    """
    try:
        url = "http://localhost:8000/proxy"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and "data" in data and "proxy" in data["data"]:
                return data["data"]["proxy"]
        return ""
    except Exception as e:
        print(f"获取代理失败: {str(e)}")
        return ""

async def search_and_download(image_path):
    """
    执行循环搜索和下载过程
    
    Args:
        image_path: 初始图片路径
        proxy: 代理设置
    """
    spider = BaiduSimilarImageSpider()
    
    # 读取初始图片
    logger.info(f"开始循环搜索，初始图片: {image_path}")
    images_name = os.listdir(image_path)
    logger.info(f"共 {len(images_name)} 张图片")
    total_image_num = 0
    for image_name in images_name:
        logger.info(f"开始第 {total_image_num}/{len(images_name)} 张图片的搜索")
        logger.info(f"使用图片进行搜索: {image_name} ")
        with open(os.path.join(image_path, image_name), "rb") as f:
            image_bytes = f.read()
        # 1. 使用图片搜索相似图片
        proxy = get_proxy()
        logger.info(f"使用代理: {proxy}")
        search_url = await spider(image_bytes=image_bytes, proxy=proxy)
        
        if not search_url:
            logger.error("搜索失败，终止循环")
            break
        
        # 2. 获取相似图片URL列表
        images_url = await spider.postprocess(search_url)
        if not images_url:
            logger.error("未找到相似图片，终止循环")
            break
        
        logger.info(f"找到 {len(images_url)} 张相似图片")
        
        # 3. 下载相似图片
        proxy = get_proxy()
        logger.info(f"使用代理下载图片: {proxy}")
        downloaded_files = await download_images(images_url, proxy)
        if not downloaded_files:
            logger.error("下载图片失败，终止循环")
            break
        
        logger.info(f"成功下载 {len(downloaded_files)} 张图片")
        total_image_num += len(downloaded_files)

    logger.info(f"总共下载 {total_image_num} 张图片")
    logger.info("循环搜索完成")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="循环搜索和下载相似图片")
    parser.add_argument("--image", type=str, default="./test_image/", help="初始图片路径")
    
    args = parser.parse_args()
    
    # 确保初始图片存在
    if not os.path.exists(args.image):
        logger.error(f"初始图片不存在: {args.image}")
        exit(1)
    
    # 运行循环搜索
    asyncio.run(search_and_download(args.image))

    


