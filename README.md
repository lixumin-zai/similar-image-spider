# similar-image-spider
For building a dataset to obtain similar images.

### support
- search engines
    - baidu
    - google

- proxy
    - http & https
    - auto update 
    - fastapi server
```shell
# use
cd proxy/
python proxy_api.py

# curl http://localhost:8000/proxy
```

### Known Issues
- **Problem**: The search results may sometimes include advertising images or irrelevant product covers instead of the desired similar images.
  
  ![Advertising Images Example](./static/image.png)

- **Solution**: Use an image similarity comparison model to perform precise filtering and remove these irrelevant results.

