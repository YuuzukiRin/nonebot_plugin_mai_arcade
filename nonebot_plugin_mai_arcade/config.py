"""
配置和数据管理模块
"""
import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

import nonebot
from nonebot import get_plugin_config

require = nonebot.require
require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store


class SmartTipRule(BaseModel):
    """一条等待时间提示规则，按 max_minutes 升序匹配。"""

    max_minutes: int
    tip: str


class Config(BaseModel):
    """插件配置类

    nearcade_api_token: Nearcade 开发者 API 令牌，用于把机厅人数同步到云端。
        可在 https://nearcade.cn/settings/api-tokens 生成。
        不配置时人数仍会正常统计与落盘，只是不往 Nearcade 上传。
    count_smart_tips: 排队等待时间提示规则列表，按 max_minutes 升序匹配，
        max_minutes=0 表示无需等待。
    """

    nearcade_api_token: Optional[str] = None
    count_smart_tips: list[SmartTipRule] = [
        SmartTipRule(max_minutes=0, tip="✅ 无需等待，快去出勤吧！"),
        SmartTipRule(max_minutes=20, tip="✅ 舞萌启动！"),
        SmartTipRule(max_minutes=40, tip="🕰️ 小排队还能忍"),
        SmartTipRule(max_minutes=90, tip="💀 DBD，纯折磨，建议换店"),
        SmartTipRule(max_minutes=9999, tip="🪦 建议回家（或者明天再来）"),
    ]


#: 从 bot 的 .env 读取的插件配置
plugin_config = get_plugin_config(Config)

# 驱动层配置
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
