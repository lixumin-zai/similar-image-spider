import requests
import random
import json
import re

class ProxyManager:
    """代理管理类"""
    
    def __init__(self):
        self.proxy_api_url = "https://github.com/MrMarble/proxy-list/raw/refs/heads/main/all.txt"
        self.proxies = self.get_proxies()

    def get_proxies(self):
        """从GitHub代理池仓库获取代理列表"""
        try:
            # 获取代理列表
            response = requests.get(self.proxy_api_url)
            proxy_list = []
            
            # 解析每行JSON数据
            for line in response.text.split('\n'):
                if line:
                    try:
                        # 使用正则表达式匹配IP地址和端口格式
                        pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)'
                        match = re.match(pattern, line)
                        if match:
                            ip, port = match.groups()
                            proxy = f"http://{ip}:{port}"
                            proxy_list.append(proxy)
                    except:
                        continue
            
            return proxy_list
        except:
            return []
    
    def get_random_proxy(self):
        """随机获取一个代理"""
        if self.proxies:
            return random.choice(self.proxies)
        return None
        
    def test_proxy(self, proxy=None, timeout=5):
        """测试代理是否可用，默认访问百度
        
        Args:
            proxy (str, optional): 要测试的代理地址，格式为 http://ip:port。如果为None则随机获取一个代理
            timeout (int, optional): 请求超时时间，默认5秒
            
        Returns:
            tuple: (是否可用, 代理地址, 错误信息)
        """
        if proxy is None:
            proxy = self.get_random_proxy()
            
        if not proxy:
            return False, None, "未获取到代理"
            
        try:
            # 设置代理格式
            proxies = {
                'http': proxy,
                # 'https': proxy
            }
            # 尝试访问百度
            response = requests.get('https://www.baidu.com', proxies=proxies, timeout=timeout)
            if response.status_code == 200:
                return True, proxy, f"状态码: {response.status_code}"
            else:
                return False, proxy, f"状态码: {response.status_code}"
        except Exception as e:
            return False, proxy, str(e)

if __name__ == "__main__":
    # 创建代理管理器实例
    proxy_manager = ProxyManager()
    # 获取随机代理
    proxy = proxy_manager.get_random_proxy()
    print(f"获取到的随机代理: {proxy}")
    
    # 测试代理是否可用
    success, test_proxy, message = proxy_manager.test_proxy(proxy)
    if success:
        print(f"代理测试成功! {message}")
    else:
        print(f"代理测试失败! {message}")


# curl --proxy 'https://170.106.115.219:13001' https://baidu.com
