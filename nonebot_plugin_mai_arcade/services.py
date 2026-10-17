"""
外部服务和API调用模块

插件里所有对外 HTTP 请求都收敛在这里，统一使用 ``httpx.AsyncClient``：
原版在 handler 中直接用阻塞的 ``http.client`` 发请求，会卡住整个事件循环。
"""
from __future__ import annotations

import urllib.parse
from typing import Any

import httpx
from nonebot import logger

from .config import data_json, plugin_config, re_write_json
from .logic import pick_maimai_game

#: 请求头，部分网关会校验 UA
USER_AGENT = "Mozilla/5.0 (compatible; NoneBot-Arcade-Plugin)"

#: Nearcade API 地址与单次请求超时
BASE_URL = "https://nearcade.cn"
TIMEOUT = 10.0

#: Nearcade 新版网页地址带了来源段（``/shops/bemanicn/{id}``），但 API 并不接受它：
#: nearcade 来源的机厅用 ``/api/shops/bemanicn/{id}`` 会 404 或返回空数据。
#: 因此以不带来源的路径为主，仅在查不到时再试一次带前缀的。
SOURCE_PREFIXES: tuple[str, ...] = ("", "bemanicn")


class NearcadeError(RuntimeError):
    """Nearcade 接口调用失败（网络异常或非 2xx 响应）。"""

    def __init__(self, message: str, *, status: int | None = None, body: str = ""):
        self.status = status
        self.body = body
        super().__init__(message)


def _headers(*, auth: bool = False) -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if auth:
        if not plugin_config.nearcade_api_token:
            raise NearcadeError(
                "尚未配置 Nearcade API Token，无法上传人数。"
                "请到 https://nearcade.cn/settings/api-tokens 生成后，"
                "填入 bot 的 .env：NEARCADE_API_TOKEN=..."
            )
        headers["Authorization"] = f"Bearer {plugin_config.nearcade_api_token}"
    return headers


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    auth: bool = False,
) -> httpx.Response:
    """向 Nearcade 发一次请求，非 2xx 抛 :class:`NearcadeError`。"""
    headers = _headers(auth=auth)
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
            response = await client.request(
                method, path, params=params, json=json_body, headers=headers
            )
    except httpx.HTTPError as e:
        raise NearcadeError(f"请求 Nearcade 失败：{e}") from e

    if response.status_code >= 400:
        raise NearcadeError(
            f"Nearcade 返回 HTTP {response.status_code}",
            status=response.status_code,
            body=response.text[:200],
        )
    return response


def _shop_paths(shop_id: int | str, suffix: str = "") -> list[str]:
    return [
        f"/api/shops/{prefix + '/' if prefix else ''}{shop_id}{suffix}"
        for prefix in SOURCE_PREFIXES
    ]


def _looks_like_shop(payload: dict[str, Any], suffix: str) -> bool:
    """判断响应是否真的命中了机厅。

    详情接口看有没有 ``shop``；出勤接口在查不到时会返回 ``total=0`` 且 ``games`` 为空，
    而正常机厅即使没人出勤也会带上 ``games``，所以以 ``games`` 是否为空来区分。
    """
    if suffix:
        return bool(payload.get("games"))
    return bool(payload.get("shop"))


async def _fetch_shop_payload(shop_id: int | str, suffix: str = "") -> dict[str, Any]:
    """按 ``/api/shops/{id}`` 取机厅数据，必要时退回带来源前缀的路径。"""
    last_error: NearcadeError | None = None
    fallback: dict[str, Any] | None = None

    for path in _shop_paths(shop_id, suffix):
        try:
            payload = (await _request("GET", path)).json()
        except (NearcadeError, ValueError) as e:
            last_error = e if isinstance(e, NearcadeError) else NearcadeError(str(e))
            continue
        if _looks_like_shop(payload, suffix):
            return payload
        if fallback is None:
            fallback = payload

    if fallback is not None:
        return fallback
    raise last_error or NearcadeError(f"查询机厅 {shop_id} 失败")


# ---------------------------------------------------------------- 机厅检索


async def search_nearcade_shops(keyword: str, page: int = 1, limit: int = 3) -> dict:
    """搜索 nearcade 机厅，返回 ``{'shops': [...], 'totalCount': int}``。

    失败时记日志并返回空结果，避免指令直接报错。
    """
    params = {"q": keyword, "page": page, "limit": limit}
    try:
        data = (await _request("GET", "/api/shops", params=params)).json()
    except (NearcadeError, ValueError) as e:
        logger.error(f"搜索nearcade机厅失败: {e}")
        return {"shops": [], "totalCount": 0}

    return {
        "shops": [s for s in (data.get("shops") or []) if isinstance(s, dict)],
        "totalCount": int(data.get("totalCount") or 0),
    }


# ---------------------------------------------------------------- 机厅详情


async def fetch_shop(shop_id: int | str) -> dict[str, Any]:
    """读取机厅详情（``data['shop']``）。"""
    return (await _fetch_shop_payload(shop_id)).get("shop") or {}


async def fetch_maimai_game(shop_id: int | str) -> tuple[int | None, int]:
    """读取机厅详情，返回舞萌机台的 ``(gameId, 机台数)``。"""
    return pick_maimai_game((await fetch_shop(shop_id)).get("games") or [])


# ---------------------------------------------------------------- 人数同步


async def fetch_attendance(shop_id: int | str) -> int:
    """读取机厅当前的云端出勤人数（``total``）。"""
    payload = await _fetch_shop_payload(shop_id, "/attendance")
    return int(payload.get("total") or 0)


async def update_attendance(shop_id: int | str, game_id: int, count: int) -> None:
    """把机厅人数同步到 Nearcade，失败抛 :class:`NearcadeError`。

    400 一般表示机厅在 Nearcade 上处于关店状态，调用方可以据此给出更友好的提示。
    """
    body = {"games": [{"id": game_id, "currentAttendances": count}]}
    try:
        await _request(
            "POST", f"/api/shops/{shop_id}/attendance", json_body=body, auth=True
        )
    except NearcadeError as e:
        if e.status != 404:
            raise
        await _request(
            "POST",
            f"/api/shops/bemanicn/{shop_id}/attendance",
            json_body=body,
            auth=True,
        )


# ---------------------------------------------------------------- 发现 / 地图


async def call_discover(lat: float, lon: float, radius: int = 10, name: str | None = None):
    """调用 nearcade 发现 API，返回 ``(机厅数据, 网页URL)``。"""
    params = {"latitude": str(lat), "longitude": str(lon), "radius": str(radius)}
    if name:
        params["name"] = name

    query = urllib.parse.urlencode(params, safe="")
    web_url = f"{BASE_URL}/discover?{query}"
    try:
        data = (await _request("GET", "/api/discover", params=params)).json()
    except (NearcadeError, ValueError) as e:
        logger.error(f"调用发现API失败: {e}")
        return {}, web_url

    return data, web_url


async def auto_add_arcade_map(group_id: str, arcade_name: str, shop_url: str) -> bool:
    """自动添加机厅地图，返回是否真正新增。"""
    if not shop_url or group_id not in data_json or arcade_name not in data_json[group_id]:
        return False

    maps = data_json[group_id][arcade_name].setdefault("map", [])
    if shop_url in maps:
        return False

    maps.append(shop_url)
    await re_write_json()
    return True
