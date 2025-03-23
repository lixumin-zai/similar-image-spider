import requests
import asyncio
import aiohttp, aiofiles
import os
import re
import json
import logging
from aiohttp import ClientTimeout

from user_agent import UserAgent

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Settings:
    def __init__(self):

        self.upload_image_api = "https://graph.baidu.com/upload"

        self.upload_timeout = 60
        self.upload_connect_timeout = 10
        self.upload_sock_connect_timeout = 20
        self.upload_sock_read_timeout = 20
        self.upload_max_retries = 4

        self.max_page_size = 300



class SimilarImageSpider:
    def __init__(self, settings):
                                # "https://graph.baidu.com/s?card_key=&entrance=GENERAL&extUiData%5BisLogoShow%5D=1&f=all&isLogoShow=1&session_id=10220954735134965298&sign=1214cab84394301e4275101742746910&tpl_from=pc"
        self.baidu_search_url = "https://graph.baidu.com/ajax/similardetailnew?card_key=common&carousel=1&contsign=&curAlbum=0&entrance=GENERAL&f=general&image=&index=0&inspire=common&jumpIndex=&next=2&pageFrom=graph_upload_wise&page_size={settings.max_page_size}&render_type=card_all&session_id={session_id}&sign={sign}&srcp=&wd=&page=1"
        self.settings = settings

    async def search_image(
        self,
        image_path: str, 
        headers: dict
    ) -> str:
        async with aiohttp.ClientSession() as session:
            async with aiofiles.open(image_path, 'rb') as f:
                content = await f.read()
                logger.info(f"开始上传图像: {image_path}，图像文件内容大小: {len(content)} bytes")
                # logger.info(f"开始上传: {image_path}")

                timeout = ClientTimeout(
                        total=self.settings.upload_timeout,  # 设置整个请求的超时
                        connect=self.settings.upload_connect_timeout,  # 设置连接的超时
                        sock_connect=self.settings.upload_sock_connect_timeout,  # 设置套接字连接超时
                        sock_read=self.settings.upload_sock_read_timeout  # 设置读取数据的超时
                )
                retries = 0
                while retries < self.settings.upload_max_retries:
                    try:
                        form = aiohttp.FormData()
                        form.add_field('image', content, filename='image.jpg', content_type='image/jpeg')

                        async with session.post(self.settings.upload_image_api, headers=headers, data=form, ssl=False, timeout=timeout) as response:
                            text = await response.text()
                            if response.status == 200:
                                resp_data = await response.json()
                                search_url_base = resp_data["data"]["url"]
                                session_id = re.search(r'session_id=([0-9]+)', search_url_base).group(1)
                                sign = re.search(r'sign=([a-fA-F0-9]+)', search_url_base).group(1)

                                search_url = f"https://graph.baidu.com/ajax/similardetailnew?card_key=common&carousel=1&contsign=&curAlbum=0&entrance=GENERAL&f=general&image=&index=0&inspire=common&jumpIndex=&next=2&pageFrom=graph_upload_wise&page_size={self.settings.max_page_size}&render_type=card_all&session_id={session_id}&sign={sign}&srcp=&wd=&page=1"
                                logger.debug(f"图像上传成功，URL: {search_url}")
                                return search_url
                            else:
                                logger.error(f"图像上传失败，状态码: {response.status}, URL: {image_path}")
                                if 403 == response.status:
                                    retries += 1
                                    logger.error(f"被流控，上传失败: {image_path}, 重试 {retries}/{self.settings.upload_max_retries}")
                                    if retries < self.settings.upload_max_retries:
                                        await asyncio.sleep(5 ** retries)  # 指数退避
                                    else:
                                        logger.error(f"已达到最大重试次数，放弃上传: {image_path}")
                                        return None
                                else:
                                    return None

                    except aiohttp.ClientError as e:
                        retries += 1
                        logger.error(f"网络错误，无法上传图像: {image_path}, 错误信息: {str(e)} - 重试 {retries}/{self.settings.upload_max_retries}")
                        if retries < self.settings.upload_max_retries:
                            await asyncio.sleep(2 ** retries)  # 指数退避
                        else:
                            logger.error(f"已达到最大重试次数，放弃上传: {image_path}")
                            return None
                    
                    except Exception as e:
                        logger.error(f"上传图像时出错: {image_path}, 错误信息: {str(e)}")
                        raise


async def fech(image_path, headers):
    async with aiohttp.ClientSession() as session:
        search_url = await search_image(
            session=session,
            image_path=image_path, 
            headers=headers
        )
        return search_url

def spider(image_root_path="", save_path=""):
    user_agent = UserAgent()
    settings = Settings()
    spider = SimilarImageSpider(settings)

    headers = {"User-Agent": user_agent()}
    search_urls = []
    for image_name in os.listdir(image_root_path):
        image_path = image_root_path + image_name
        search_url = asyncio.run(spider.search_image(image_path, headers))
        search_urls.append(search_url)
        response = requests.get(search_url, headers=headers)
        resp_data = response.json()
        with open(f"{save_path}/{image_name.split('.')[0]}.json", "w") as f:
            json.dump(resp_data, f, ensure_ascii=False)
    # 全部链接
    with open("./output/url.txt", "w") as f:
        for search_url in search_urls:
            print(search_url)
            f.write(search_url+"\n")

if __name__ == "__main__":
    spider("./test_image/", "./output/")


