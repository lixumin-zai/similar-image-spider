from user_agent import UserAgent
import requests
import asyncio
import aiohttp
from utils import upload_image
import os
import json


class SimilarImageSpider:
    def __init__(self):
        self.baidu_search_url = "https://graph.baidu.com/ajax/similardetailnew?card_key=common&carousel=1&contsign=&curAlbum=0&entrance=GENERAL&f=general&image=&index=0&inspire=common&jumpIndex=&next=2&pageFrom=graph_upload_wise&page_size={settings.max_page_size}&render_type=card_all&session_id={session_id}&sign={sign}&srcp=&wd=&page=1"


async def search_image(
        session: aiohttp.client.ClientSession,
        image_path: str, 
        headers: dict
) -> str:
    async with aiofiles.open(image_path, 'rb') as f:
        content = await f.read()
        logging.info(f"开始上传图像: {image_path}，图像文件内容大小: {len(content)} bytes")
        # logging.info(f"开始上传: {image_path}")

        timeout = ClientTimeout(
                total=settings.upload_timeout,  # 设置整个请求的超时
                connect=settings.upload_connect_timeout,  # 设置连接的超时
                sock_connect=settings.upload_sock_connect_timeout,  # 设置套接字连接超时
                sock_read=settings.upload_sock_read_timeout  # 设置读取数据的超时
        )
        retries = 0
        while retries < settings.upload_max_retries:
            try:
                form = aiohttp.FormData()
                form.add_field('image', content, filename='image.jpg', content_type='image/jpeg')

                async with session.post(settings.upload_image_api, headers=headers, data=form, ssl=False, timeout=timeout) as response:
                    text = await response.text()
                    if response.status == 200:
                        resp_data = await response.json()
                        search_url_base = resp_data["data"]["url"]
                        session_id = re.search(r'session_id=([0-9]+)', search_url_base).group(1)
                        sign = re.search(r'sign=([a-fA-F0-9]+)', search_url_base).group(1)

                        search_url = 
                        logger.debug(f"图像上传成功，URL: {search_url}")
                        return search_url
                    else:
                        logger.error(f"图像上传失败，状态码: {response.status}, URL: {image_path}")
                        if 403 == response.status:
                            retries += 1
                            logging.error(f"被流控，上传失败: {image_path}, 重试 {retries}/{settings.upload_max_retries}")
                            if retries < settings.upload_max_retries:
                                await asyncio.sleep(5 ** retries)  # 指数退避
                            else:
                                logging.error(f"已达到最大重试次数，放弃上传: {image_path}")
                                return None
                        else:
                            return None

            except aiohttp.ClientError as e:
                retries += 1
                logging.error(f"网络错误，无法上传图像: {image_path}, 错误信息: {str(e)} - 重试 {retries}/{settings.upload_max_retries}")
                if retries < settings.upload_max_retries:
                    await asyncio.sleep(2 ** retries)  # 指数退避
                else:
                    logging.error(f"已达到最大重试次数，放弃上传: {image_path}")
                    return None
            
            except Exception as e:
                logging.error(f"上传图像时出错: {image_path}, 错误信息: {str(e)}")
                raise


async def fech(image_path, headers):
    async with aiohttp.ClientSession() as session:
        search_url = await upload_image(
            session=session,
            image_path=image_path, 
            headers=headers
        )
        return search_url

def spider(image_root_path="", save_path=""):
    ua_generator = UAGenerator()
    headers = {"User-Agent": ua_generator.random_useragent()}
    search_urls = []
    for image_name in os.listdir(image_root_path):
        image_path = image_root_path + image_name
        search_url = asyncio.run(fech(image_path, headers))
        search_urls.append(search_urls)
        response = requests.get(search_url, headers=headers)
        resp_data = response.json()
        with open(f"{save_path}/{image_name.split('.')[0]}.json", "w") as f:
            json.dump(resp_data, f)
    # 全部链接
    with open("./url.txt", "w") as f:
        for search_url in search_urls:
            f.write(search_url+"\n")

if __name__ == "__main__":
    spider("", "")


