"""
外部服务和API调用模块
"""
import httpx
from nonebot import logger
from .config import data_json, re_write_json
from .utils import format_shop_info, get_shop_url


async def search_nearcade_shops(keyword: str, page: int = 1, limit: int = 3) -> dict:
    """
    搜索nearcade机厅
    
    Args:
        keyword: 搜索关键词
        page: 页码
        limit: 返回结果数量限制
        
    Returns:
        包含shops和totalCount的字典
    """
    try:
        import urllib.parse
        
        encoded_query = urllib.parse.quote(keyword)
        url = f"https://nearcade.phizone.cn/api/shops?q={encoded_query}&page={page}&limit={limit}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; NoneBot-Arcade-Plugin)',
            'Accept': 'application/json'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return {
                'shops': data.get('shops', []),
                'totalCount': data.get('totalCount', 0)
            }
    except Exception as e:
        logger.error(f"搜索nearcade机厅失败: {e}")
        return {'shops': [], 'totalCount': 0}


async def auto_add_arcade_map(group_id: str, arcade_name: str, shop_url: str) -> bool:
    """
    自动添加机厅地图
    
    Args:
        group_id: 群组ID
        arcade_name: 机厅名称
        shop_url: 机厅URL
        
    Returns:
        是否成功添加地图
    """
    try:
        if not shop_url or group_id not in data_json or arcade_name not in data_json[group_id]:
            return False
        
        # 初始化map字段
        if 'map' not in data_json[group_id][arcade_name]:
            data_json[group_id][arcade_name]['map'] = []
        
        # 检查URL是否已存在
        if shop_url not in data_json[group_id][arcade_name]['map']:
            data_json[group_id][arcade_name]['map'].append(shop_url)
            await re_write_json()
            return True
        
        return False
    except Exception as e:
        logger.error(f"自动添加机厅地图失败: {e}")
        return False


async def call_discover(lat: float, lon: float, radius: int = 10, name: str = None):
    """
    调用nearcade发现API，根据位置查找附近机厅
    
    Args:
        lat: 纬度
        lon: 经度
        radius: 搜索半径（公里）
        name: 位置名称（可选）
        
    Returns:
        tuple: (机厅数据, 网页URL)
    """
    try:
        import urllib.parse
        
        BASE_HOST = "nearcade.phizone.cn"
        params = {
            "latitude": str(lat),
            "longitude": str(lon),
            "radius": str(radius),
        }
        if name:
            params["name"] = name
        
        query = urllib.parse.urlencode(params, safe="")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://{BASE_HOST}/api/discover?{query}")
            response.raise_for_status()
            data = response.json()
            web_url = f"https://{BASE_HOST}/discover?{query}"
            return data, web_url
    except Exception as e:
        logger.error(f"调用发现API失败: {e}")
        return {}, ""