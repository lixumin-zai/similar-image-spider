import os
import json
import time
import asyncio
import aiohttp
import logging
import requests

from datetime import datetime
from get_proxy import ProxyManager

# 配置日志
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class ProxyPool:
    """代理池管理类，用于存储和管理可用代理"""
    
    def __init__(self, pool_file="../static/proxy_pool.json", expire_minutes=1):
        """
        初始化代理池
        
        Args:
            pool_file (str): 代理池存储文件路径
            expire_minutes (int): 代理过期时间(分钟)
        """
        self.pool_file = pool_file
        self.expire_minutes = expire_minutes
        self.proxy_manager = ProxyManager()
        self.used_proxies = set()  # 已使用过的代理集合
        self.available_proxies = []  # 可用代理列表
        self.load_pool()
    
    def load_pool(self):
        """从文件加载代理池"""
        if os.path.exists(self.pool_file):
            try:
                with open(self.pool_file, 'r') as f:
                    data = json.load(f)
                    
                    # 加载已使用的代理
                    self.used_proxies = set(data.get('used_proxies', []))
                    
                    # 加载并过滤过期的可用代理
                    current_time = time.time()
                    self.available_proxies = []
                    
                    for proxy_info in data.get('available_proxies', []):
                        # 检查代理是否过期
                        if current_time - proxy_info['timestamp'] < self.expire_minutes * 60:
                            self.available_proxies.append(proxy_info)
                logger.info(f"从文件加载了 {len(self.available_proxies)} 个可用代理和 {len(self.used_proxies)} 个已使用代理")
            except Exception as e:
                logger.error(f"加载代理池文件出错: {str(e)}")
                self.available_proxies = []
    
    def save_pool(self):
        """保存代理池到文件"""
        data = {
            'used_proxies': list(self.used_proxies),
            'available_proxies': self.available_proxies
        }
        
        try:
            with open(self.pool_file, 'w') as f:
                json.dump(data, f)
            logger.debug(f"代理池已保存到文件: {self.pool_file}")
        except Exception as e:
            logger.error(f"保存代理池文件出错: {str(e)}")
    
    def add_proxy(self, proxy, test_result=None):
        """
        添加一个可用代理到池中
        
        Args:
            proxy (str): 代理地址
            test_result (str, optional): 测试结果信息
        """
        if proxy not in self.used_proxies and not any(p['proxy'] == proxy for p in self.available_proxies):
            proxy_info = {
                'proxy': proxy,
                'timestamp': time.time(),
                'added_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'test_result': test_result
            }
            self.available_proxies.append(proxy_info)
            logger.info(f"添加新代理到池中: {proxy}, 测试结果: {test_result}")
            self.save_pool()

    def test_proxy(self, proxy, timeout=2):
        """
        测试代理是否可用
        
        Args:
            proxy (str): 代理地址
            
        Returns:
            tuple: (是否可用, 代理地址, 错误信息)
        """
        try:
            # 设置代理格式
            proxies = {
                'http': proxy,
                'https': proxy
            }
            start_time = time.time()
            response = requests.get('https://mms1.baidu.com/it/u=3609773648,115186739&fm=253&app=138&f=JPEG?w=690&h=148', proxy=proxies, timeout=timeout)
            if response.status == 200:
                elapsed = time.time() - start_time
                logger.debug(f"代理测试成功: {proxy}, 响应时间: {elapsed:.2f}秒")
                return True, proxy, f"状态码: {response.status}, 响应时间: {elapsed:.2f}秒"
            else:
                logger.debug(f"代理测试失败: {proxy}, 状态码: {response.status}")
                return False, proxy, f"状态码: {response.status}"
        except Exception as e:
            logger.debug(f"代理测试异常: {proxy}, 错误: {str(e)}")
            return False, proxy, str(e)

    
    def get_proxy(self):
        """
        获取一个可用代理，并将其标记为已使用
        
        Returns:
            str: 代理地址，如果没有可用代理则返回None
        """
        if not self.available_proxies:
            logger.info("代理池为空，尝试刷新代理池")
            self.refresh_pool()
            
        while self.available_proxies:
            proxy_info = self.available_proxies.pop(0)
            proxy = proxy_info['proxy']
            success, _, message = self.proxy_manager.test_proxy(proxy)
            if success:
                self.used_proxies.add(proxy)
                logger.info(f"获取代理: {proxy}")
                self.save_pool()
                return proxy
            else:
                logger.warning(f"代理测试失败: {proxy}, 错误: {message}")
            
        logger.warning("没有可用代理")
        return None
    
    async def test_proxy_async(self, proxy, timeout=5):
        """
        异步测试代理是否可用
        
        Args:
            proxy (str): 代理地址
            timeout (int): 超时时间(秒)
            
        Returns:
            tuple: (是否可用, 代理地址, 错误信息)
        """
        try:
            # 设置代理格式
            proxies = {
                'http': proxy,
                'https': proxy
            }
            
            # 使用aiohttp异步测试
            async with aiohttp.ClientSession() as session:
                try:
                    start_time = time.time()
                    async with session.get('https://www.baidu.com', proxy=proxy, timeout=timeout) as response:
                        if response.status == 200:
                            elapsed = time.time() - start_time
                            logger.debug(f"代理测试成功: {proxy}, 响应时间: {elapsed:.2f}秒")
                            return True, proxy, f"状态码: {response.status}, 响应时间: {elapsed:.2f}秒"
                        else:
                            logger.debug(f"代理测试失败: {proxy}, 状态码: {response.status}")
                            return False, proxy, f"状态码: {response.status}"
                except Exception as e:
                    logger.debug(f"代理测试异常: {proxy}, 错误: {str(e)}")
                    return False, proxy, str(e)
        except Exception as e:
            logger.debug(f"代理测试异常: {proxy}, 错误: {str(e)}")
            return False, proxy, str(e)
    
    async def refresh_pool_async(self, min_size=30, max_size=50, concurrency=10):
        """
        异步刷新代理池，确保有足够的可用代理
        
        Args:
            min_size (int): 最小池大小
            max_size (int): 最大池大小
            concurrency (int): 并发测试数量
        """
        if len(self.available_proxies) >= min_size:
            logger.info(f"代理池中有足够的代理 ({len(self.available_proxies)}), 无需刷新")
            return
            
        logger.info("开始异步刷新代理池")
        # 获取新的代理
        new_proxies = self.proxy_manager.get_proxies()
        logger.info(f"从代理源获取了 {len(new_proxies)} 个代理")
        
        # 过滤掉已使用和已在池中的代理
        filtered_proxies = [
            proxy for proxy in new_proxies 
            if proxy not in self.used_proxies and not any(p['proxy'] == proxy for p in self.available_proxies)
        ]
        logger.info(f"过滤后剩余 {len(filtered_proxies)} 个待测试代理")
        
        # 限制测试数量
        test_proxies = filtered_proxies[:max(max_size - len(self.available_proxies), 0) * 3]  # 多测试一些，提高成功率
        
        if not test_proxies:
            logger.warning("没有新的代理可以测试")
            return
            
        logger.info(f"开始测试 {len(test_proxies)} 个代理，并发数: {concurrency}")
        # 创建测试任务
        tasks = []
        for proxy in test_proxies:
            tasks.append(self.test_proxy_async(proxy))
            
        # 分批执行测试任务
        count = 0
        for i in range(0, len(tasks), concurrency):
            batch = tasks[i:i+concurrency]
            logger.debug(f"测试第 {i//concurrency + 1} 批代理，数量: {len(batch)}")
            results = await asyncio.gather(*batch)
            
            for success, proxy, message in results:
                if success and count < (max_size - len(self.available_proxies)):
                    self.add_proxy(proxy, message)
                    count += 1
                    
                if count >= (max_size - len(self.available_proxies)):
                    break
            
            if count >= (max_size - len(self.available_proxies)):
                break
        
        logger.info(f"代理池刷新完成，新增 {count} 个可用代理，当前可用代理总数: {len(self.available_proxies)}")
    
    def refresh_pool(self, min_size=10, max_size=50):
        """
        刷新代理池，确保有足够的可用代理
        
        Args:
            min_size (int): 最小池大小
            max_size (int): 最大池大小
        """
        if len(self.available_proxies) >= min_size:
            logger.info(f"代理池中有足够的代理 ({len(self.available_proxies)}), 无需刷新")
            return
            
        logger.info("开始刷新代理池")
        # 调用异步刷新方法
        asyncio.run(self.refresh_pool_async(min_size, max_size))
        logger.info(f"代理池刷新完成，当前可用代理总数: {len(self.available_proxies)}")
    
    # 在 ProxyPool 类中添加一个异步版本的 clear_expired 方法
    async def clear_expired_async(self):
        """异步清除过期的代理"""
        current_time = time.time()
        self.available_proxies = [
            proxy_info for proxy_info in self.available_proxies
            if current_time - proxy_info['timestamp'] < self.expire_minutes * 60
        ]
        self.save_pool()
        logger.info(f"清除过期代理后，剩余可用代理: {len(self.available_proxies)}")

    async def retest_used_proxies_async(self, max_retest=100, concurrency=10):
        """
        异步重新测试已使用的代理，将仍然可用的代理重新加入到可用代理池
        
        Args:
            max_retest (int): 最大重新测试数量
            concurrency (int): 并发测试数量
        """
        if not self.used_proxies:
            logger.info("没有已使用的代理需要重新测试")
            return
            
        logger.info(f"开始重新测试已使用的代理，总数: {len(self.used_proxies)}")
        
        # 将集合转换为列表，以便可以限制测试数量
        test_proxies = list(self.used_proxies)[:max_retest]
        
        # 创建测试任务
        tasks = []
        for proxy in test_proxies:
            tasks.append(self.test_proxy_async(proxy))
            
        # 分批执行测试任务
        recovered_count = 0
        for i in range(0, len(tasks), concurrency):
            batch = tasks[i:i+concurrency]
            logger.debug(f"重新测试第 {i//concurrency + 1} 批代理，数量: {len(batch)}")
            results = await asyncio.gather(*batch)
            
            for success, proxy, message in results:
                if success:
                    # 从已使用代理集合中移除
                    self.used_proxies.remove(proxy)
                    # 添加到可用代理列表
                    self.add_proxy(proxy, f"重新测试通过: {message}")
                    recovered_count += 1
        
        logger.info(f"已使用代理重新测试完成，恢复了 {recovered_count} 个代理到可用池")
        self.save_pool()


if __name__ == "__main__":
    # 测试代理池
    pool = ProxyPool()
    
    # 刷新代理池
    logger.info("刷新代理池...")
    pool.refresh_pool()
    
    # 获取代理
    proxy = pool.get_proxy()
    logger.info(f"获取到的随机代理: {proxy}")
    
    # 显示可用代理数量
    logger.info(f"可用代理数量: {len(pool.available_proxies)}")
    logger.info(f"已使用代理数量: {len(pool.used_proxies)}")
    
    # 异步测试示例
    async def test_async():
        logger.info("开始异步刷新代理池...")
        await pool.refresh_pool_async(min_size=5, max_size=20, concurrency=5)
        logger.info(f"异步刷新后可用代理数量: {len(pool.available_proxies)}")
    
    # 运行异步测试
    asyncio.run(test_async())