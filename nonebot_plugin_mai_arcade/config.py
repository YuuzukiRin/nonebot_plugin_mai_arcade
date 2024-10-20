import os
from pydantic import BaseModel
from typing import Dict, List
from nonebot import require
require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_data_dir
from pathlib import Path

class Config(BaseModel):
    mai_arcade_path: str = os.getenv("mai_arcade_path", None)
