import os
import torch
import lpips
import numpy as np
import cv2
from skimage.metrics import structural_similarity as ssim
from concurrent.futures import ProcessPoolExecutor, as_completed
from PIL import Image
import torchvision.transforms as transforms

# 每个进程加载一次 LPIPS 模型，避免重复加载和多进程 Pickling 问题
_lpips_model = None

def init_worker():
    """初始化 LPIPS 模型（每个进程只执行一次）"""
    global _lpips_model
    # 自动选择计算设备 (CUDA / MPS / CPU)
    device = 'cuda' if torch.cuda.is_available() else ('mps' if torch.backends.mps.is_available() else 'cpu')
    
    # 禁用 LPIPS 输出的多余 log，避免刷屏
    import logging
    logging.getLogger('lpips').setLevel(logging.ERROR)
    
    # 使用 VGG 作为特征提取网络，符合人类视觉感知
    _lpips_model = lpips.LPIPS(net='vgg').to(device)
    # 禁用梯度计算以节省显存/内存
    for param in _lpips_model.parameters():
        param.requires_grad = False

def process_image(img_path, target_size=(256, 256)):
    """读取并预处理图像，统一转换为相同大小"""
    try:
        # 使用 PIL 读取
        img_pil = Image.open(img_path).convert('RGB')
        img_resized = img_pil.resize(target_size, Image.Resampling.BILINEAR)
        
        # 1. 转换为 Tensor [-1, 1] 供 LPIPS 计算使用
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
        ])
        img_tensor = transform(img_resized).unsqueeze(0)
        
        # 2. 转换为 numpy 灰度图供 SSIM 计算使用
        img_cv = cv2.cvtColor(np.array(img_resized), cv2.COLOR_RGB2BGR)
        img_gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        return img_tensor, img_gray
    except Exception as e:
        print(f"⚠️ 加载图片失败 {img_path}: {e}")
        return None, None

def compare_single_image(orig_tensor, orig_gray, comp_path):
    """比较单张图片：计算 SSIM (越高越好) 和 LPIPS (越低越好)"""
    global _lpips_model
    try:
        comp_tensor, comp_gray = process_image(comp_path)
        if comp_tensor is None:
            return comp_path, 0.0, 1.0, False
            
        # 计算 SSIM (基于灰度像素结构)，data_range=255 表示 8位 图像
        score_ssim = ssim(orig_gray, comp_gray, data_range=255)
        
        # 计算 LPIPS (基于深度学习特征，语义层面)
        device = next(_lpips_model.parameters()).device
        with torch.no_grad():
            score_lpips = _lpips_model(orig_tensor.to(device), comp_tensor.to(device)).item()
            
        return comp_path, score_ssim, score_lpips, True
    except Exception as e:
        print(f"⚠️ 对比失败 {comp_path}: {e}")
        return comp_path, 0.0, 1.0, False

class ImageSimilarityFilter:
    """图片相似度多进程过滤工具类"""
    
    def __init__(self, ssim_threshold=0.5, lpips_threshold=0.6):
        """
        :param ssim_threshold: SSIM 阈值，大于该值认为相似 (越高越好，最大1.0)
        :param lpips_threshold: LPIPS 阈值，小于该值认为相似 (越低越好，最小0.0)
        """
        self.ssim_threshold = ssim_threshold
        self.lpips_threshold = lpips_threshold
        
    def filter_images(self, orig_path, comp_paths, max_workers=4):
        """
        通过多进程并行对比，过滤掉不相似的图片
        :param orig_path: 参考原图路径
        :param comp_paths: 待比较的图片路径列表
        :param max_workers: 并行进程数
        :return: (过滤后保留的路径列表, 详细对比结果字典列表)
        """
        orig_tensor, orig_gray = process_image(orig_path)
        if orig_tensor is None:
            raise ValueError(f"无法加载参考原图: {orig_path}")
            
        results = []
        filtered_paths = []
        
        print(f"🚀 开始使用 {max_workers} 个进程并行比较 {len(comp_paths)} 张图片...")
        
        # 使用 ProcessPoolExecutor 开启多进程
        with ProcessPoolExecutor(max_workers=max_workers, initializer=init_worker) as executor:
            # 提交所有的比较任务
            future_to_path = {
                executor.submit(compare_single_image, orig_tensor, orig_gray, path): path 
                for path in comp_paths
            }
            
            # 收集完成的结果
            for future in as_completed(future_to_path):
                path, ssim_val, lpips_val, success = future.result()
                if not success:
                    continue
                    
                # 判定是否相似 (需同时满足 SSIM 和 LPIPS 的条件)
                is_similar = (ssim_val >= self.ssim_threshold) and (lpips_val <= self.lpips_threshold)
                
                results.append({
                    'path': path,
                    'ssim': ssim_val,
                    'lpips': lpips_val,
                    'is_similar': is_similar
                })
                
                if is_similar:
                    filtered_paths.append(path)
                    
        # 按照 LPIPS(升序) 和 SSIM(降序) 对结果进行排序，越相似的越靠前
        results.sort(key=lambda x: (x['lpips'], -x['ssim']))
        
        return filtered_paths, results

if __name__ == '__main__':
    # ================= 🚀 调用样例 =================
    
    # 1. 准备测试数据 (实际使用时替换为您爬取的真实图片路径)
    os.makedirs('test_images', exist_ok=True)
    orig_img = 'test_images/orig.jpg'
    
    # 为了演示，如果测试图不存在，就生成几张随机加了噪点的纯色图片
    if not os.path.exists(orig_img):
        base_img = np.ones((256, 256, 3), dtype=np.uint8) * 128
        cv2.imwrite(orig_img, base_img)
        for i in range(1, 6):
            # 噪点逐渐增加，模拟越来越不相似的图
            noise = np.random.randint(-30, 30, (256, 256, 3))
            test_img = np.clip(base_img + noise * i, 0, 255).astype(np.uint8)
            cv2.imwrite(f'test_images/comp_{i}.jpg', test_img)
            
    comp_imgs = [f'test_images/comp_{i}.jpg' for i in range(1, 6)]
    
    # 2. 初始化过滤器
    # - SSIM 一般 > 0.5 认为结构相似
    # - LPIPS 一般 < 0.6 认为语义/感知相似
    img_filter = ImageSimilarityFilter(ssim_threshold=0.5, lpips_threshold=0.6)
    
    # 3. 运行多进程过滤
    filtered_list, detailed_results = img_filter.filter_images(orig_img, comp_imgs, max_workers=4)
    
    # 4. 打印结果
    print("\n📊 --- 对比结果 ---")
    for res in detailed_results:
        status = "✅ 保留" if res['is_similar'] else "❌ 剔除"
        print(f"[{status}] {res['path']} | SSIM: {res['ssim']:.4f} (↑) | LPIPS: {res['lpips']:.4f} (↓)")
        
    print(f"\n✨ 过滤完毕: 共 {len(comp_imgs)} 张，剔除 {len(comp_imgs) - len(filtered_list)} 张，保留 {len(filtered_list)} 张。")