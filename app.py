#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import base64
import re
from typing import List
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from spider.baidu_search import BaiduSimilarImageSpider
from main import get_proxy

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="相似图片搜索API",
    description="上传图片获取相似图片URL列表",
    version="1.0.0"
)

# 初始化爬虫
spider = BaiduSimilarImageSpider()


# Pydantic模型用于base64请求
class Base64ImageRequest(BaseModel):
    image_data: str
    image_format: str = "auto"  # 可选：指定图片格式，默认自动检测


def decode_base64_image(base64_data: str) -> bytes:
    """
    解码base64图片数据
    
    Args:
        base64_data: base64编码的图片数据
        
    Returns:
        bytes: 解码后的图片字节数据
        
    Raises:
        ValueError: 如果base64数据无效
    """
    try:
        # 移除可能的data URL前缀 (如: data:image/jpeg;base64,)
        if ',' in base64_data:
            base64_data = base64_data.split(',', 1)[1]
        
        # 解码base64数据
        image_bytes = base64.b64decode(base64_data)
        
        if len(image_bytes) == 0:
            raise ValueError("解码后的图片数据为空")
            
        return image_bytes
        
    except Exception as e:
        raise ValueError(f"无效的base64图片数据: {str(e)}")


def validate_image_format(image_bytes: bytes) -> bool:
    """
    验证图片格式
    
    Args:
        image_bytes: 图片字节数据
        
    Returns:
        bool: 是否为有效的图片格式
    """
    # 检查常见图片格式的文件头
    image_signatures = {
        b'\xff\xd8\xff': 'JPEG',
        b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a': 'PNG',
        b'\x47\x49\x46\x38': 'GIF',
        b'\x42\x4d': 'BMP',
        b'\x52\x49\x46\x46': 'WEBP'
    }
    
    for signature in image_signatures:
        if image_bytes.startswith(signature):
            return True
    
    return False


@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {
        "message": "相似图片搜索API",
        "version": "1.0.0",
        "endpoints": {
            "/search-similar": "POST - 上传图片文件搜索相似图片",
            "/search-similar-base64": "POST - 使用base64图片数据搜索相似图片",
            "/docs": "GET - API文档"
        }
    }


@app.post("/search-similar")
async def search_similar_images(file: UploadFile = File(...)) -> JSONResponse:
    """
    上传图片文件并获取相似图片URL列表
    
    Args:
        file: 上传的图片文件
        
    Returns:
        JSONResponse: 包含相似图片URL列表的响应
    """
    try:
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400, 
                detail="文件必须是图片格式 (jpg, png, gif, etc.)"
            )
        
        # 读取图片字节数据
        image_bytes = await file.read()
        
        if len(image_bytes) == 0:
            raise HTTPException(
                status_code=400,
                detail="上传的文件为空"
            )
        
        logger.info(f"接收到图片文件: {file.filename}, 大小: {len(image_bytes)} bytes")
        
        return await process_image_search(image_bytes)
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"处理图片搜索时发生错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器内部错误: {str(e)}"
        )


@app.post("/search-similar-base64")
async def search_similar_images_base64(request: Base64ImageRequest) -> JSONResponse:
    """
    使用base64编码的图片数据获取相似图片URL列表
    
    Args:
        request: 包含base64图片数据的请求体
        
    Returns:
        JSONResponse: 包含相似图片URL列表的响应
    """
    try:
        # 解码base64图片数据
        try:
            image_bytes = decode_base64_image(request.image_data)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        
        # 验证图片格式
        if not validate_image_format(image_bytes):
            raise HTTPException(
                status_code=400,
                detail="无效的图片格式，支持的格式: JPEG, PNG, GIF, BMP, WEBP"
            )
        
        logger.info(f"接收到base64图片数据, 大小: {len(image_bytes)} bytes")
        
        return await process_image_search(image_bytes)
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"处理base64图片搜索时发生错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器内部错误: {str(e)}"
        )


async def process_image_search(image_bytes: bytes) -> JSONResponse:
    """
    处理图片搜索的通用函数
    
    Args:
        image_bytes: 图片字节数据
        
    Returns:
        JSONResponse: 包含相似图片URL列表的响应
    """
    # 获取代理
    proxy = None
    logger.info(f"使用代理: {proxy}")
    
    # 1. 使用图片搜索相似图片
    search_url = await spider(image_bytes=image_bytes, proxy=proxy)
    
    if not search_url:
        raise HTTPException(
            status_code=500,
            detail="搜索失败，无法获取搜索URL"
        )
    
    # 2. 获取相似图片URL列表
    images_url = await spider.postprocess(search_url)
    
    if not images_url:
        raise HTTPException(
            status_code=404,
            detail="未找到相似图片"
        )
    
    # 限制返回数量为100张
    images_url = images_url[:100]
    
    logger.info(f"找到 {len(images_url)} 张相似图片")
    
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": f"成功找到 {len(images_url)} 张相似图片",
            "data": {
                "total_count": len(images_url),
                "images_url": images_url,
                "search_url": search_url
            }
        }
    )


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "message": "服务运行正常"}


if __name__ == "__main__":
    # 启动服务器
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        # reload=True, 
        log_level="info"
    )