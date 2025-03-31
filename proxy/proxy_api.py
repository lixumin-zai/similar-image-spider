import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
from contextlib import asynccontextmanager
from proxy_pool import ProxyPool

# 配置日志
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 创建代理池实例
proxy_pool = ProxyPool(expire_minutes=1)  # 设置代理过期时间为60分钟
background_task = None

# 后台任务：定期刷新代理池
async def refresh_proxy_pool_task():
    while True:
        try:
            logger.info("开始定期刷新代理池")
            await proxy_pool.refresh_pool_async(min_size=20, max_size=100, concurrency=10)
            await proxy_pool.retest_used_proxies_async()
            logger.info(f"代理池刷新完成，当前可用代理数量: {len(proxy_pool.available_proxies)}")
            # 每1分钟刷新一次
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"刷新代理池出错: {str(e)}")
            await asyncio.sleep(10)  # 出错后等待1分钟再试

# 使用 lifespan 上下文管理器替代 on_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    logger.info("服务启动，初始化代理池")
    global background_task
    background_task = asyncio.create_task(refresh_proxy_pool_task())
    
    yield  # 这里是应用运行的地方
    
    # 关闭时执行
    logger.info("服务关闭，清理资源")
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            logger.info("后台任务已取消")
            # 创建FastAPI应用
            
app = FastAPI(
    title="代理池API",
    description="提供代理池管理和获取代理的API服务",
    version="1.0.0",
    lifespan=lifespan  # 使用 lifespan 上下文管理器
)
# 定义响应模型
class ProxyResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class ProxyListResponse(BaseModel):
    success: bool
    message: str
    data: Optional[List[Dict[str, Any]]] = None



# 获取一个代理
@app.get("/proxy", response_model=ProxyResponse, summary="获取一个可用代理")
async def get_proxy():
    proxy = proxy_pool.get_proxy()
    if proxy:
        return ProxyResponse(
            success=True,
            message="获取代理成功",
            data={"proxy": proxy}
        )
    else:
        return ProxyResponse(
            success=False,
            message="没有可用代理",
            data=None
        )

# 获取代理池状态
@app.get("/status", response_model=ProxyResponse, summary="获取代理池状态")
async def get_status():
    return ProxyResponse(
        success=True,
        message="获取代理池状态成功",
        data={
            "available_count": len(proxy_pool.available_proxies),
            "used_count": len(proxy_pool.used_proxies),
            "expire_minutes": proxy_pool.expire_minutes
        }
    )

# 获取所有可用代理
@app.get("/proxies", response_model=ProxyListResponse, summary="获取所有可用代理")
async def get_all_proxies():
    proxies = [
        {
            "proxy": p["proxy"],
            "added_time": p["added_time"],
            "test_result": p["test_result"]
        } for p in proxy_pool.available_proxies
    ]
    return ProxyListResponse(
        success=True,
        message="获取所有可用代理成功",
        data=proxies
    )

# 手动刷新代理池
@app.post("/refresh", response_model=ProxyResponse, summary="手动刷新代理池")
async def refresh_pool(background_tasks: BackgroundTasks):
    if len(proxy_pool.available_proxies) >= 20:
        return ProxyResponse(
            success=True,
            message="代理池中有足够的代理，无需刷新",
            data={"available_count": len(proxy_pool.available_proxies)}
        )
    
    # 在后台刷新代理池
    background_tasks.add_task(proxy_pool.refresh_pool, min_size=20, max_size=100)
    
    return ProxyResponse(
        success=True,
        message="正在后台刷新代理池",
        data={"available_count": len(proxy_pool.available_proxies)}
    )

# 清除过期代理
@app.post("/clear-expired", response_model=ProxyResponse, summary="清除过期代理")
async def clear_expired():
    before_count = len(proxy_pool.available_proxies)
    await proxy_pool.clear_expired_async()
    after_count = len(proxy_pool.available_proxies)
    
    return ProxyResponse(
        success=True,
        message="清除过期代理完成",
        data={
            "before_count": before_count,
            "after_count": after_count,
            "cleared_count": before_count - after_count
        }
    )

if __name__ == "__main__":
    uvicorn.run("proxy_api:app", host="0.0.0.0", port=8000)