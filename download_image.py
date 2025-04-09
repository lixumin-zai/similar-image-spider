import os
import asyncio
import aiohttp
import aiofiles
from urllib.parse import urlparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

async def download_image(session, url, save_dir, proxy=None):
    """
    异步下载单个图片
    
    Args:
        session: aiohttp会话
        url: 图片URL
        save_dir: 保存目录
        proxy: 代理地址
    
    Returns:
        保存的文件路径或None（如果下载失败）
    """
    try:
        # 从URL中提取文件名
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        
        # 如果文件名为空或没有扩展名，使用URL的哈希值作为文件名
        if not filename or '.' not in filename:
            filename = f"{hash(url)}.jpg"
        
        # 确保文件名唯一
        save_path = os.path.join(save_dir, filename)
        count = 1
        while os.path.exists(save_path):
            name, ext = os.path.splitext(filename)
            save_path = os.path.join(save_dir, f"{name}_{count}{ext}")
            count += 1
        
        # 发送请求下载图片
        async with session.get(url, proxy=proxy) as response:
            if response.status == 200:
                # 异步写入文件
                async with aiofiles.open(save_path, 'wb') as f:
                    await f.write(await response.read())
                logger.info(f"成功下载: {url} -> {save_path}")
                return save_path
            else:
                logger.error(f"下载失败 {url}, 状态码: {response.status}")
                return None
    except Exception as e:
        logger.error(f"下载 {url} 时出错: {str(e)}")
        return None

async def download_images(images_url, proxy=None, max_concurrent=10):
    """
    异步下载多个图片
    
    Args:
        images_url: 图片URL列表
        proxy: 代理地址
        max_concurrent: 最大并发数
    
    Returns:
        成功下载的图片路径列表
    """
    # 创建保存目录
    save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download_image")
    os.makedirs(save_dir, exist_ok=True)
    
    # 设置连接池限制和超时
    conn = aiohttp.TCPConnector(limit=max_concurrent)
    timeout = aiohttp.ClientTimeout(total=60)
    
    # 创建会话
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        # 使用信号量限制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_with_semaphore(url):
            async with semaphore:
                return await download_image(session, url, save_dir, proxy)
        
        # 创建下载任务
        tasks = [download_with_semaphore(url) for url in images_url]
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤出成功的下载
        successful_downloads = [r for r in results if r is not None and not isinstance(r, Exception)]
        
        logger.info(f"下载完成: 总计 {len(images_url)} 张图片, 成功 {len(successful_downloads)} 张")
        return successful_downloads

def download_images_sync(images_url, proxy=None, max_concurrent=10):
    """
    同步接口，调用异步下载函数
    
    Args:
        images_url: 图片URL列表
        proxy: 代理地址
        max_concurrent: 最大并发数
    
    Returns:
        成功下载的图片路径列表
    """
    return asyncio.run(download_images(images_url, proxy, max_concurrent))

if __name__ == "__main__":
    # 示例用法
    urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.png",
        "https://example.com/image3.jpeg",
    ]
    
    # 可选的代理设置
    # proxy = "http://127.0.0.1:7890"
    proxy = None
    
    # 下载图片
    downloaded_files = download_images_sync(urls, proxy)
    print(f"下载的文件: {downloaded_files}")