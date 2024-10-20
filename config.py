import os
from pydantic import BaseModel, Extra
from typing import Dict, List
from nonebot import require
require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_data_dir
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Config(BaseModel, extra=Extra.ignore):
    mai_arcade_path: str = os.getenv("mai_arcade_path", None)
