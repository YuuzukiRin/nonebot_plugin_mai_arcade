"""
配置和数据管理模块
"""
import json
from pathlib import Path
import nonebot
require = nonebot.require
require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

# 配置
config = nonebot.get_driver().config
superusers = config.superusers
block_group = set(["12345678"])
search_sessions = {}  # 存储搜索会话状态

# 数据文件路径
arcade_data_file: Path = store.get_plugin_data_file("arcade_data.json")
arcade_marker_file: Path = store.get_plugin_data_file("arcade_cache_marker.json")

# 初始化数据文件
if not arcade_data_file.exists():
    arcade_data_file.write_text('{}', encoding='utf-8')

# 全局数据变量
data_json = {}

def load_data():
    """加载数据文件"""
    global data_json
    with open(arcade_data_file, 'r', encoding='utf-8') as f:
        data_json = json.load(f)

async def re_write_json():
    """保存数据到文件"""
    global data_json
    with open(arcade_data_file, 'w', encoding='utf-8') as f:
        json.dump(data_json, f, ensure_ascii=False, indent=2)

# 初始化加载数据
load_data()