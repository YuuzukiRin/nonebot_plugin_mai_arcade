from pydantic import BaseModel, Extra
from typing import Dict, List
from nonebot import require

require("nonebot_plugin_localstore")

from nonebot_plugin_localstore import get_data_dir

class Config(BaseModel, extra=Extra.ignore):
    mai_arcade_path: str = get_data_dir("mai_arcade")
