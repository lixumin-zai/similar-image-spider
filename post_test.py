# -*- coding: utf-8 -*-
# @Time    :   2025/10/28 09:47:45
# @Author  :   lixumin
# @FileName:   post_test.py


import requests
import base64

def test():
    url = "http://localhost:8000/search-similar-base64"
    with open("/Users/lixumin/Desktop/projects/similar-image-spider/test_image/1.jpg", "rb") as f:
        image_data = f.read()
        image_data = base64.b64encode(image_data).decode("utf-8")

    response = requests.post(url, json={
        "image_data": image_data
    })
    
    print(response.text)


if __name__ == "__main__":
    test()