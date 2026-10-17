"""
人数管理模块

负责机厅人数的上报、重置与查询，并在更新后把结果同步到 Nearcade。
纯计算逻辑见 :mod:`nonebot_plugin_mai_arcade.logic`，网络请求见 :mod:`nonebot_plugin_mai_arcade.services`。
"""
import datetime

from nonebot import logger, on_regex, on_endswith
from nonebot.adapters.onebot.v11 import GroupMessageEvent

from ..config import block_group, data_json, plugin_config, re_write_json
from ..logic import (
    apply_operator,
    extract_shop_id,
    match_arcade,
    parse_count_command,
    render_status,
    render_upload_reply,
    strip_query_suffix,
)
from ..services import (
    NearcadeError,
    fetch_attendance,
    fetch_maimai_game,
    update_attendance,
)


sv_arcade = on_regex(r"^([\u4e00-\u9fa5\w]+)\s*(==\d+|={1}\d+|\+\+\d+|--\d+|\+\+|--|[+-]?\d+)?$", priority=100)
sv_arcade_on_fullmatch = on_endswith(("几", "几人", "j"), ignorecase=False, priority=100)


def _render(name: str, num: int, machine_count: int, **kwargs) -> str:
    """按 .env 里的 COUNT_SMART_TIPS 渲染状态文本。"""
    return render_status(name, num, machine_count, tips=plugin_config.count_smart_tips, **kwargs)


@sv_arcade.handle()
async def handle_sv_arcade(event: GroupMessageEvent):
    """处理 ``<机厅名>++/--/+num/=num`` 形式的人数更新。"""
    group_id = str(event.group_id)
    current_time = datetime.datetime.now().strftime("%H:%M")

    parsed = parse_count_command(event.raw_message)
    if parsed is None:
        return
    name, op, num = parsed

    if (not op) and (num is None):
        return

    matched_name = match_arcade(data_json.get(group_id) or {}, name)
    if matched_name is None:
        return

    arcade_data = data_json[group_id][matched_name]
    num_list = arcade_data.setdefault("num", [])
    current_num = sum(num_list) if num_list else 0

    try:
        new_num, delta = apply_operator(op, num, current_num)
    except ValueError as e:
        await sv_arcade.finish(str(e))
        return

    if delta:
        num_list.append(delta)
    else:
        num_list.clear()
        num_list.append(new_num)

    arcade_data["last_updated_by"] = event.sender.nickname
    arcade_data["last_updated_at"] = current_time
    arcade_data.pop("previous_update_by", None)
    arcade_data.pop("previous_update_at", None)
    await re_write_json()

    maps = arcade_data.get("map") or []
    shop_id = extract_shop_id(maps[0]) if maps else None
    if shop_id is None:
        # 没有配置地图链接：只更新本地人数
        await sv_arcade.finish(f"[{matched_name}] 当前人数更新为 {new_num}\n由 {event.sender.nickname} 于 {current_time} 更新")
        return

    # 与云端人数对齐：把云端的增量叠加到本地人数上
    try:
        cloud_num = await fetch_attendance(shop_id)
    except (NearcadeError, ValueError) as e:
        logger.warning(f"获取 shop {shop_id} 云端出勤人数失败: {e}")
        cloud_num = None
    if cloud_num is not None and cloud_num != current_num:
        new_num += cloud_num - current_num
        num_list.clear()
        num_list.append(new_num)

    try:
        game_id, machine_count = await fetch_maimai_game(shop_id)
    except (NearcadeError, ValueError) as e:
        await sv_arcade.finish(f"获取 shop {shop_id} 信息失败: {e}")
        return

    if game_id is None:
        await sv_arcade.finish(f"获取 shop {shop_id} 信息失败: 未找到可用机台")
        return

    arcade_data["coutnum"] = machine_count
    await re_write_json()

    msg = _render(matched_name, new_num, machine_count, verb="人数已更新为")

    upload_error = None
    try:
        await update_attendance(shop_id, game_id, new_num)
    except NearcadeError as e:
        upload_error = e

    if group_id in block_group:
        # 调试群只更新数据，不回复
        return

    await sv_arcade.finish(render_upload_reply(msg, upload_error))


@sv_arcade_on_fullmatch.handle()
async def handle_sv_arcade_on_fullmatch(event: GroupMessageEvent):
    """处理 ``<机厅名>几人`` / ``几`` / ``j``，展示云端最新人数与等待建议。"""
    group_id = str(event.group_id)

    name_part = strip_query_suffix(event.raw_message)
    if name_part is None:
        return

    arcade_name = match_arcade(data_json.get(group_id) or {}, name_part)
    if arcade_name is None:
        return

    arcade_info = data_json[group_id][arcade_name]
    num_list = arcade_info.setdefault("num", [])
    maps = arcade_info.get("map") or []
    shop_id = extract_shop_id(maps[0]) if maps else None

    current_num = sum(num_list)
    machine_count = arcade_info.get("coutnum", 1)
    last_updated_by = arcade_info.get("last_updated_by")
    last_updated_at = arcade_info.get("last_updated_at")

    if shop_id is not None:
        try:
            cloud_num = await fetch_attendance(shop_id)
        except (NearcadeError, ValueError) as e:
            await sv_arcade_on_fullmatch.finish(f"获取 shop {shop_id} 云端出勤人数失败: {e}")
            return

        if cloud_num != current_num:
            num_list.clear()
            num_list.append(cloud_num)
            current_num = cloud_num
            last_updated_by, last_updated_at = "Nearcade", None
            await re_write_json()

        try:
            _, machine_count = await fetch_maimai_game(shop_id)
            arcade_info["coutnum"] = machine_count
            await re_write_json()
        except (NearcadeError, ValueError) as e:
            logger.warning(f"获取 shop {shop_id} 机台信息失败: {e}")

    if not num_list:
        await sv_arcade_on_fullmatch.finish(f"[{arcade_name}] 今日人数尚未更新\n你可以爽霸机了\n快去出勤吧！")

    await sv_arcade_on_fullmatch.finish(
        _render(
            arcade_name,
            current_num,
            machine_count,
            updated_by=last_updated_by,
            updated_at=last_updated_at,
        )
    )
