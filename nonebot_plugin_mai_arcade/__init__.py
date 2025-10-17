import datetime
import http.client
import json
from nonebot.plugin import PluginMetadata
from nonebot import require, get_driver, on_endswith, on_command, on_regex, on_fullmatch, on_message
from nonebot.adapters import Bot, Event, Message
from nonebot.adapters.onebot.v11 import MessageSegment, GroupMessageEvent, MessageEvent
from nonebot.params import CommandArg, EventMessage
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from pathlib import Path
import nonebot
import math
import urllib.parse
require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store
import re

config = nonebot.get_driver().config
block_group = ["765883672"]
__plugin_meta__ = PluginMetadata(
    name="nonebot_plugin_mai_arcade",
    description="NoneBot2插件 用于为舞萌玩家提供机厅人数上报、线上排卡等功能支持",
    usage="",
    type="application",
    homepage="https://github.com/YuuzukiRin/nonebot_plugin_mai_arcade",
    supported_adapters={"~onebot.v11"},
)

arcade_data_file: Path = store.get_plugin_data_file("arcade_data.json")

if not arcade_data_file.exists():
    arcade_data_file.write_text('{}', encoding='utf-8')

arcade_marker_file: Path = store.get_plugin_data_file("arcade_cache_marker.json")


def load_data():
    global data_json
    with open(arcade_data_file, 'r', encoding='utf-8') as f:
        data_json = json.load(f)


load_data()

go_on = on_command("上机")
get_in = on_command("排卡")
get_run = on_command("退勤")
show_list = on_command("排卡现状")
add_group = on_command("添加群聊")
delete_group = on_command("删除群聊")
shut_down = on_command("闭店")
add_arcade = on_command("添加机厅")
delete_arcade = on_command("删除机厅")
show_arcade = on_command("机厅列表")
put_off = on_command("延后")
add_alias = on_command("添加机厅别名")
delete_alias = on_command("删除机厅别名", aliases={"移除机厅别名"})
get_arcade_alias = on_command("机厅别名")
add_arcade_map = on_command("添加机厅地图")
delete_arcade_map = on_command("删除机厅地图", aliases={"移除机厅地图"})
get_arcade_map = on_command("机厅地图", aliases={"音游地图"})
sv_arcade = on_regex(r"^([\u4e00-\u9fa5\w]+)\s*(==\d+|={1}\d+|\+\+\d+|--\d+|\+\+|--|[+-]?\d+)?$", priority=100)
sv_arcade_on_fullmatch = on_endswith(("几", "几人", "j"), ignorecase=False)
query_updated_arcades = on_fullmatch(("mai", "机厅人数", "jtj", "机厅几人"), ignorecase=False)
arcade_help = on_command("机厅help", aliases={"机厅帮助", "arcade help"}, priority=100, block=True)
scheduler = require('nonebot_plugin_apscheduler').scheduler
driver = get_driver()


async def ensure_daily_clear():
    """On startup or first message after restart, clear stale data if daily reset hasn't run yet."""
    # Today's date in Asia/Shanghai
    today = datetime.datetime.now().date().isoformat()

    try:
        marker = json.loads(arcade_marker_file.read_text(encoding='utf-8'))
    except Exception:
        marker = {}

    if marker.get('cleared_date') == today:
        return  # already cleared today

    # Not cleared yet today -> perform clear
    await clear_data_daily()


@driver.on_startup
async def _on_startup_clear():
    await ensure_daily_clear()


superusers = config.superusers
location_listener = on_message(priority=100, block=False)
blockgroup = on_command("静默监听模式", aliases={"静默模式", "监听模式"}, permission=SUPERUSER)
blockdetelgroup = on_command("关闭静默监听模式", aliases={"关闭静默模式", "关闭监听模式"}, permission=SUPERUSER)


def is_superuser_or_admin(event: GroupMessageEvent) -> bool:
    user_id = str(event.user_id)
    return event.sender.role in ["admin", "owner"] or user_id in superusers


@blockgroup.handle()
async def blockmodel(bot: Bot, event: GroupMessageEvent):
    group_id = str(event.group_id)
    block_group.append(group_id)
    await blockgroup.finish(f"以将{group_id}加入BlockGroup List，进行静默监听模式")


@blockdetelgroup.handle()
async def blockmodel(bot: Bot, event: GroupMessageEvent):
    group_id = str(event.group_id)
    block_group.remove(group_id)
    await blockgroup.finish(f"以将{group_id}从BlockGroup List删除，改为正常模式")


@scheduler.scheduled_job('cron', hour=0, minute=0)
async def clear_data_daily():
    """Reset per-arcade counts once per day (Asia/Shanghai). Also persists a daily marker."""
    global data_json
    # Determine today's date in Asia/Shanghai; fall back to local if zoneinfo missing
    today = datetime.datetime.now().date().isoformat()

    # Clear counters
    for group_id, arcades in data_json.items():
        for arcade_name, info in arcades.items():
            if 'last_updated_by' in info:
                info['last_updated_by'] = None
            if 'last_updated_at' in info:
                info['last_updated_at'] = None
            if 'num' in info:
                info['num'] = []

    # Persist changes and write marker
    try:
        await re_write_json()
    except Exception:
        pass
    try:
        arcade_marker_file.write_text(json.dumps({'cleared_date': today}, ensure_ascii=False), encoding='utf-8')
    except Exception:
        pass

    print("arcade缓存清理完成")


@arcade_help.handle()
async def _(event: GroupMessageEvent, message: Message = EventMessage()):
    await arcade_help.send(
        "机厅人数:\n"
        "[<机厅名>++/--] 机厅的人数+1/-1\n"
        "[<机厅名>+num/-num] 机厅的人数+num/-num\n"
        "[<机厅名>=num/<机厅名>num] 机厅的人数重置为num\n"
        "[<机厅名>几/几人/j] 展示机厅当前的人数信息\n"
        "[mai/机厅人数] 展示当日已更新的所有机厅的人数列表\n"
        "群聊管理:\n"
        "[添加群聊] (管理)将群聊添加到JSON数据中\n"
        "[删除群聊] (管理)从JSON数据中删除指定的群聊\n"
        "机厅管理:\n"
        "[添加机厅] (管理)将机厅添加到群聊\n"
        "[删除机厅] (管理)从群聊中删除指定的机厅\n"
        "[机厅列表] 展示当前机厅列表\n"
        "[添加机厅别名] (管理)为机厅添加别名\n"
        "[删除机厅别名] (管理)移除机厅的别名\n"
        "[机厅别名] 展示机厅别名\n"
        "[添加机厅地图] (管理)添加机厅地图信息\n"
        "[删除机厅地图] (管理)移除机厅地图信息\n"
        "[机厅地图] 展示机厅音游地图\n"
        "排卡功能:\n"
        "[上机] 将当前第一位排队的移至最后\n"
        "[排卡] 加入排队队列\n"
        "[退勤] 从排队队列中退出\n"
        "[排卡现状] 展示当前排队队列的情况\n"
        "[延后] 将自己延后一位\n"
        "[闭店] (管理)清空排队队列\n"
    )


@add_alias.handle()
async def handle_add_alias(bot: Bot, event: GroupMessageEvent):
    global data_json

    input_str = event.raw_message.strip()
    group_id = str(event.group_id)

    if not input_str.startswith("添加机厅别名"):
        await add_alias.finish("格式错误：添加机厅别名 <店名> <别名>")
        return

    parts = input_str.split(maxsplit=2)
    if len(parts) != 3:
        await add_alias.finish("格式错误：添加机厅别名 <店名> <别名>")
        return

    _, name, alias = parts

    if group_id in data_json:
        if not is_superuser_or_admin(event):
            await add_alias.finish("只有管理员能够添加机厅别名")
            return

        if name not in data_json[group_id]:
            await add_alias.finish(f"店名 '{name}' 不在群聊中或为机厅别名，请先添加该机厅或使用该机厅本名")
            return

        if alias in data_json[group_id][name].get("alias_list", []):
            await add_alias.finish(f"别名 '{alias}' 已存在，请使用其他别名")
            return

        # Add alias to the specified arcade
        alias_list = data_json[group_id][name].get("alias_list", [])
        alias_list.append(alias)
        data_json[group_id][name]["alias_list"] = alias_list

        await re_write_json()

        await add_alias.finish(f"已成功为 '{name}' 添加别名 '{alias}'")
    else:
        await add_alias.finish("本群尚未开通排卡功能，请联系群主或管理员添加群聊")


@delete_alias.handle()
async def handle_delete_alias(bot: Bot, event: GroupMessageEvent):
    global data_json

    input_str = event.raw_message.strip()
    group_id = str(event.group_id)

    if not input_str.startswith("删除机厅别名"):
        await delete_alias.finish("格式错误：删除机厅别名 <店名> <别名>")
        return

    parts = input_str.split(maxsplit=2)
    if len(parts) != 3:
        await delete_alias.finish("格式错误：删除机厅别名 <店名> <别名>")
        return

    _, name, alias = parts

    if group_id in data_json:
        if not is_superuser_or_admin(event):
            await delete_alias.finish("只有管理员能够删除机厅别名")
            return

        if name not in data_json[group_id]:
            await delete_alias.finish(f"店名 '{name}' 不在群聊中或为机厅别名，请先添加该机厅或使用该机厅本名")
            return

        alias_list = data_json[group_id][name].get("alias_list", [])
        if alias not in alias_list:
            await delete_alias.finish(f"别名 '{alias}' 不存在，请检查输入的别名")
            return

        alias_list.remove(alias)
        data_json[group_id][name]["alias_list"] = alias_list

        await re_write_json()

        await delete_alias.finish(f"已成功删除 '{name}' 的别名 '{alias}'")
    else:
        await delete_alias.finish("本群尚未开通排卡功能，请联系群主或管理员添加群聊")


@get_arcade_alias.handle()
async def handle_get_arcade_alias(bot: Bot, event: GroupMessageEvent):
    global data_json

    group_id = str(event.group_id)
    input_str = event.raw_message.strip()

    if not input_str.startswith("机厅别名"):
        return

    parts = input_str.split(maxsplit=1)
    if len(parts) != 2:
        await get_arcade_alias.finish("格式错误：机厅别名 <机厅>")
        return

    _, query_name = parts

    if group_id in data_json:
        found = False
        for name in data_json[group_id]:
            # Check if it matches an alias in the hall name or alias list
            if name == query_name or (
                    'alias_list' in data_json[group_id][name] and query_name in data_json[group_id][name][
                'alias_list']):
                found = True
                if 'alias_list' in data_json[group_id][name] and data_json[group_id][name]['alias_list']:
                    aliases = data_json[group_id][name]['alias_list']
                    reply = f"机厅 '{name}' 的别名列表如下：\n"
                    for index, alias in enumerate(aliases, start=1):
                        reply += f"{index}. {alias}\n"
                    await get_arcade_alias.finish(reply.strip())
                else:
                    await get_arcade_alias.finish(f"机厅 '{name}' 尚未添加别名")
                break

        if not found:
            await get_arcade_alias.finish(f"找不到机厅或机厅别名为 '{query_name}' 的相关信息")
    else:
        await get_arcade_alias.finish("本群尚未开通相关功能，请联系群主或管理员添加群聊")


@sv_arcade.handle()
async def handle_sv_arcade(bot: Bot, event: GroupMessageEvent, state: T_State):
    global data_json

    input_str = event.raw_message.strip()
    group_id = str(event.group_id)
    current_time = datetime.datetime.now().strftime("%H:%M")

    pattern = re.compile(r'^([\u4e00-\u9fa5\w]+?)([+\-=]{0,2})(\d*)$')
    match = pattern.match(input_str)
    if not match:
        return

    name, op, num_str = match.groups()
    num = int(num_str) if num_str else None

    if (not op) and (num is None):
        return

    if group_id not in data_json:
        return

    found = False
    if name in data_json[group_id]:
        found = True
    else:
        for arcade_name, arcade_info in data_json[group_id].items():
            if "alias_list" in arcade_info and name in arcade_info["alias_list"]:
                name = arcade_name
                found = True
                break

    if not found:
        return

    arcade_data = data_json[group_id][name]
    num_list = arcade_data.setdefault("num", [])
    current_num = sum(num_list) if num_list else 0

    if op in ("++", "+"):
        delta = num if num else 1
        if abs(delta) > 50:
            await sv_arcade.finish("检测到非法数值，拒绝更新")
        new_num = current_num + delta
        if new_num < 0 or new_num > 100:
            await sv_arcade.finish("检测到非法数值，拒绝更新")
    elif op in ("--", "-"):
        delta = -(num if num else 1)
        if abs(delta) > 50:
            await sv_arcade.finish("检测到非法数值，拒绝更新")
        new_num = current_num + delta
        if new_num < 0 or new_num > 100:
            await sv_arcade.finish("检测到非法数值，拒绝更新")
    elif op in ("==", "=") or (op == "" and num is not None):
        new_num = num
        if new_num < 0 or new_num > 100:
            await sv_arcade.finish("检测到非法数值，拒绝更新")
        delta = 0
        num_list.clear()
        num_list.append(new_num)
    else:
        return

    if op in ("++", "+", "--", "-"):
        num_list.append(delta)
    arcade_data["last_updated_by"] = event.sender.nickname
    arcade_data["last_updated_at"] = current_time
    arcade_data.pop("previous_update_by", None)
    arcade_data.pop("previous_update_at", None)
    await re_write_json()

    try:
        shop_id = re.search(r'/shop/(\d+)', arcade_data['map'][0]).group(1)
    except KeyError:
        await sv_arcade.finish(f"[{name}] 当前人数更新为 {new_num}\n由 {event.sender.nickname} 于 {current_time} 更新")

    conn = http.client.HTTPSConnection("nearcade.phizone.cn")
    conn.request("GET", f"/api/shops/bemanicn/{shop_id}")
    res = conn.getresponse()
    if res.status != 200:
        await sv_arcade.finish(f"获取 shop {shop_id} 信息失败: {res.status}")

    raw_data = res.read().decode("utf-8")
    data = json.loads(raw_data)
    game_id = data["shop"]["games"][0]["gameId"]
    coutnum = 0
    for game in data["shop"]["games"]:
        if game["name"] == "maimai DX":
            coutnum = game.get("quantity", 1)
    arcade_data["coutnum"] = coutnum
    await re_write_json()

    per_round_minutes = 16
    players_per_round = max(int(coutnum), 1) * 2  # 每轮最多游玩人数（至少按1台计算）
    queue_num = max(int(new_num) - players_per_round, 0)  # 等待人数（不包含正在玩的这一轮）

    if queue_num > 0:
        expected_rounds = queue_num / players_per_round  # 平均轮数（允许小数）
        min_rounds = queue_num // players_per_round  # 乐观整数轮（可能为0）
        max_rounds = math.ceil(queue_num / players_per_round)  # 保守整数轮

        wait_time_avg = round(expected_rounds * per_round_minutes)
        wait_time_min = int(min_rounds * per_round_minutes)
        wait_time_max = int(max_rounds * per_round_minutes)

        if wait_time_avg <= 20:
            smart_tip = "✅ 舞萌启动！"
        elif 20 < wait_time_avg <= 40:
            smart_tip = "🕰️ 小排队还能忍"
        elif 40 < wait_time_avg <= 90:
            smart_tip = "💀 DBD，纯折磨，建议换店"
        else:  # > 90
            smart_tip = "🪦 建议回家（或者明天再来）"

        msg = (
            f"📍 {name}  人数已更新为 {new_num}\n"
            f"🕹️ 机台数量：{coutnum} 台（每轮 {players_per_round} 人）\n\n"
            f"⌛ 预计等待：约 {wait_time_avg} 分钟\n"
            f"   ↳ 范围：{wait_time_min}~{wait_time_max} 分钟（{min_rounds}~{max_rounds} 轮）\n\n"
            f"💡 {smart_tip}"
        )
    else:
        # 无需等待
        msg = (
            f"📍 {name}  人数已更新为 {new_num}\n"
            f"🕹️ 机台数量：{coutnum} 台（每轮 {players_per_round} 人）\n\n"
            f"✅ 无需等待，快去出勤吧！"
        )

    payload = json.dumps({
        "games": [
            {"id": game_id, "currentAttendances": new_num}
        ]
    })
    headers = {
        'Authorization': 'Bearer nk_eimMHQaX7F6g0LlLg6ihhweRQTyLxUTVKHuIdijadC',
        'Content-Type': 'application/json'
    }

    try:
        conn = http.client.HTTPSConnection("nearcade.phizone.cn", timeout=10)
        conn.request("POST", f"/api/shops/bemanicn/{shop_id}/attendance", payload, headers)
        res = conn.getresponse()
        raw_data = res.read().decode("utf-8")
    except Exception as e:
        raw_data = str(e)
        res = None

    if res is not None and res.status == 200:
        if group_id in block_group:
            return
        else:
            await sv_arcade.finish(f"感谢使用，机厅人数已上传 Nearcade\n{msg}")
    else:
        if group_id in block_group:
            return
        status_text = res.status if res is not None else "请求失败"
        await sv_arcade.finish(f"上传失败: {status_text}\n返回信息: {raw_data}\n\n{msg}")


@sv_arcade_on_fullmatch.handle()
async def handle_sv_arcade_on_fullmatch(bot: Bot, event: Event, state: T_State):
    global data_json

    input_str = event.raw_message.strip()
    group_id = str(event.group_id)

    pattern = r'^([\u4e00-\u9fa5\w]+)([几j]\d*人?)$'
    match = re.match(pattern, input_str)
    if not match:
        return
    name_part = match.group(1).strip()
    num_part = match.group(2).strip()

    if group_id in data_json:
        found_arcade = None
        if name_part in data_json[group_id]:
            found_arcade = name_part
        else:
            for arcade_name, arcade_info in data_json[group_id].items():
                alias_list = arcade_info.get("alias_list", [])
                if name_part in alias_list:
                    found_arcade = arcade_name
                    break

        if found_arcade:
            arcade_info = data_json[group_id][found_arcade]
            num_list = arcade_info.setdefault("num", [])
            try:
                shop_id = re.search(r'/shop/(\d+)', arcade_info['map'][0]).group(1)
                conn = http.client.HTTPSConnection("nearcade.phizone.cn")
                conn.request("GET", f"/api/shops/bemanicn/{shop_id}/attendance")
                res = conn.getresponse()
                if res.status != 200:
                    await sv_arcade.send(f"获取 shop {shop_id} 云端出勤人数失败: {res.status}")
                raw_data = res.read().decode("utf-8")
                data = json.loads(raw_data)
                regnum = data["total"]
                num_list = num_list
                current_num = sum(num_list)
                if regnum == current_num:
                    if group_id in block_group:
                        return
                    last_updated_by = arcade_info.get("last_updated_by")
                    last_updated_at = arcade_info.get("last_updated_at")
                else:
                    cha = current_num - regnum
                    num_list.clear()
                    num_list.append(regnum)
                    current_num = sum(num_list)
                    if group_id in block_group:
                        if data_json[group_id][found_arcade]["alias_list"]:
                            jtname = data_json[group_id][found_arcade]["alias_list"][0]
                        else:
                            jtname = found_arcade
                        await sv_arcade_on_fullmatch.finish(f"{jtname}+{cha}")
                    else:
                        last_updated_by = "Nearcade"
                        last_updated_at = "None"
                if not num_list:
                    await sv_arcade_on_fullmatch.finish(
                        f"[{found_arcade}] 今日人数尚未更新\n你可以爽霸机了\n快去出勤吧！")
                else:
                    coutnum = arcade_info.get("quantity", 1)
                    per_round_minutes = 16
                    players_per_round = max(int(coutnum), 1) * 2  # 每轮最多游玩人数（至少按1台计算）
                    queue_num = max(int(current_num) - players_per_round, 0)  # 等待人数（不包含正在玩的这一轮）

                    if queue_num > 0:
                        expected_rounds = queue_num / players_per_round
                        min_rounds = queue_num // players_per_round
                        max_rounds = math.ceil(queue_num / players_per_round)

                        wait_time_avg = round(expected_rounds * per_round_minutes)
                        wait_time_min = int(min_rounds * per_round_minutes)
                        wait_time_max = int(max_rounds * per_round_minutes)

                        if wait_time_avg <= 20:
                            smart_tip = "✅ 舞萌启动！"
                        elif 20 < wait_time_avg <= 40:
                            smart_tip = "🕰️ 小排队还能忍"
                        elif 40 < wait_time_avg <= 90:
                            smart_tip = "💀 DBD，纯折磨，建议换店"
                        else:  # > 90
                            smart_tip = "🪦 建议回家（或者明天再来）"

                        msg = (
                            f"📍 {found_arcade}  人数为 {current_num}\n"
                            f"🕹️ 机台数量：{coutnum} 台（每轮 {players_per_round} 人）\n\n"
                            f"⌛ 预计等待：约 {wait_time_avg} 分钟\n"
                            f"   ↳ 范围：{wait_time_min}~{wait_time_max} 分钟（{min_rounds}~{max_rounds} 轮）\n\n"
                            f"💡 {smart_tip}"
                        )
                    else:
                        # 无需等待
                        msg = (
                            f"📍 {found_arcade}  人数为 {current_num}\n"
                            f"🕹️ 机台数量：{coutnum} 台（每轮 {players_per_round} 人）\n\n"
                            f"✅ 无需等待，快去出勤吧！"
                        )

                    if last_updated_at and last_updated_by:
                        msg += f"\n（{last_updated_by} · {last_updated_at}）"

                    await sv_arcade_on_fullmatch.finish(msg)
            except KeyError:
                if not num_list:
                    await sv_arcade_on_fullmatch.finish(
                        f"[{found_arcade}] 今日人数尚未更新\n你可以爽霸机了\n快去出勤吧！")
                else:
                    current_num = sum(num_list)
                    last_updated_by = arcade_info.get("last_updated_by")
                    last_updated_at = arcade_info.get("last_updated_at")
                    await re_write_json()
                    coutnum = arcade_info.get("quantity", 1)
                    per_round_minutes = 16
                    players_per_round = max(int(coutnum), 1) * 2  # 每轮最多游玩人数（至少按1台计算）
                    queue_num = max(int(current_num) - players_per_round, 0)  # 等待人数（不包含正在玩的这一轮）

                    if queue_num > 0:
                        expected_rounds = queue_num / players_per_round
                        min_rounds = queue_num // players_per_round
                        max_rounds = math.ceil(queue_num / players_per_round)

                        wait_time_avg = round(expected_rounds * per_round_minutes)
                        wait_time_min = int(min_rounds * per_round_minutes)
                        wait_time_max = int(max_rounds * per_round_minutes)

                        if wait_time_avg <= 20:
                            smart_tip = "✅ 舞萌启动！"
                        elif 20 < wait_time_avg <= 40:
                            smart_tip = "🕰️ 小排队还能忍"
                        elif 40 < wait_time_avg <= 90:
                            smart_tip = "💀 DBD，纯折磨，建议换店"
                        else:  # > 90
                            smart_tip = "🪦 建议回家（或者明天再来）"

                        msg = (
                            f"📍 {found_arcade}  人数为 {current_num}\n"
                            f"🕹️ 机台数量：{coutnum} 台（每轮 {players_per_round} 人）\n\n"
                            f"⌛ 预计等待：约 {wait_time_avg} 分钟\n"
                            f"   ↳ 范围：{wait_time_min}~{wait_time_max} 分钟（{min_rounds}~{max_rounds} 轮）\n\n"
                            f"💡 {smart_tip}"
                        )
                    else:
                        # 无需等待
                        msg = (
                            f"📍 {found_arcade}  人数为 {current_num}\n"
                            f"🕹️ 机台数量：{coutnum} 台（每轮 {players_per_round} 人）\n\n"
                            f"✅ 无需等待，快去出勤吧！"
                        )

                    if last_updated_at and last_updated_by:
                        msg += f"\n（{last_updated_by} · {last_updated_at}）"

                    await sv_arcade_on_fullmatch.finish(msg)
        else:
            # await sv_arcade_on_fullmatch.finish(f"群聊 '{group_id}' 中不存在机厅或机厅别名 '{name_part}'")
            return
    else:
        # await sv_arcade_on_fullmatch.finish(f"群聊 '{group_id}' 中不存在任何机厅")
        return


@query_updated_arcades.handle()
async def handle_query_updated_arcades(bot: Bot, event: Event, state: T_State):
    global data_json
    group_id = str(event.group_id)

    reply_messages = []
    if group_id in block_group:
        return
    group_data = data_json.get(group_id, {})
    for arcade_name, arcade_info in group_data.items():
        try:
            shop_id = re.search(r'/shop/(\d+)', arcade_info['map'][0]).group(1)
            conn = http.client.HTTPSConnection("nearcade.phizone.cn")
            conn.request("GET", f"/api/shops/bemanicn/{shop_id}/attendance")
            res = conn.getresponse()
            if res.status != 200:
                await sv_arcade.send(f"获取 shop {shop_id} 云端出勤人数失败: {res.status}")
                num_list = arcade_info.get("num", [])
                if not num_list:
                    continue
            else:
                raw_data = res.read().decode("utf-8")
                data = json.loads(raw_data)
                regnum = data["total"]
                num_list = arcade_info.get("num", [])
                current_num = sum(num_list)
                if regnum == current_num:
                    if group_id in block_group:
                        return
                    last_updated_by = arcade_info.get("last_updated_by")
                    last_updated_at = arcade_info.get("last_updated_at")
                else:
                    cha = current_num - regnum
                    num_list.clear()
                    num_list.append(regnum)
                    current_num = sum(num_list)
                    if group_id in block_group:
                        if arcade_info["alias_list"]:
                            jtname = arcade_info["alias_list"][0]
                        else:
                            jtname = arcade_name
                        await sv_arcade_on_fullmatch.finish(f"{jtname}+{cha}")
                    else:
                        last_updated_by = "Nearcade"
                        last_updated_at = "None"
        except KeyError:
            num_list = arcade_info.get("num", [])
            if not num_list:
                continue

            current_num = sum(num_list)
            last_updated_at = arcade_info.get("last_updated_at", "未知时间")
            last_updated_by = arcade_info.get("last_updated_by", "未知用户")

        line = f"[{arcade_name}] {current_num}人 \n（{last_updated_by} · {last_updated_at}）"
        reply_messages.append(line)

    if reply_messages:
        header = "📋 今日机厅人数更新情况\n\n"
        await query_updated_arcades.finish(header + "\n".join(reply_messages))
    else:
        await query_updated_arcades.finish("📋 今日机厅人数更新情况\n\n暂无更新记录\n您可以爽霸机了")


@go_on.handle()
async def handle_function(bot: Bot, event: GroupMessageEvent):
    global data_json
    group_id = str(event.group_id)
    user_id = str(event.get_user_id())
    nickname = event.sender.nickname
    if group_id in data_json:
        for n in data_json[group_id]:
            if nickname in data_json[group_id][n]['list']:
                group_list = data_json[group_id][n]['list']
                if (len(group_list) > 1 and nickname == group_list[0]):
                    msg = "收到，已将" + str(n) + "机厅中" + group_list[0] + "移至最后一位,下一位上机的是" + group_list[
                        1] + ",当前一共有" + str(len(group_list)) + "人"
                    tmp_name = [nickname]
                    data_json[group_id][n]['list'] = data_json[group_id][n]['list'][1:] + tmp_name
                    await re_write_json()
                    await go_on.finish(MessageSegment.text(msg))
                elif (len(group_list) == 1 and nickname == group_list[0]):
                    msg = "收到," + str(n) + "机厅人数1人,您可以爽霸啦"
                    await go_on.finish(MessageSegment.text(msg))
                else:
                    await go_on.finish(f"暂时未到您,请耐心等待")
        await go_on.finish(f"您尚未排卡")
    else:
        await go_on.finish(f"本群尚未开通排卡功能,请联系群主或管理员添加群聊")


@get_in.handle()
async def handle_function(bot: Bot, event: GroupMessageEvent, name_: Message = CommandArg()):
    global data_json

    name = str(name_)
    group_id = str(event.group_id)
    user_id = str(event.get_user_id())
    nickname = event.sender.nickname

    if group_id in data_json:
        for n in data_json[group_id]:
            if nickname in data_json[group_id][n]['list']:
                await go_on.finish(f"您已加入或正在其他机厅排卡")

        found = False
        target_room = None

        for room_name, room_data in data_json[group_id].items():
            if room_name == name:
                found = True
                target_room = room_name
                break
            elif 'alias_list' in room_data and name in room_data['alias_list']:
                found = True
                target_room = room_name
                break

        if found:
            tmp_name = [nickname]
            data_json[group_id][target_room]['list'] = data_json[group_id][target_room]['list'] + tmp_name
            await re_write_json()
            msg = f"收到，您已加入排卡。当前您位于第{len(data_json[group_id][target_room]['list'])}位。"
            await go_on.finish(MessageSegment.text(msg))
        elif not name:
            await go_on.finish("请输入机厅名称")
        else:
            await go_on.finish("没有该机厅，请使用添加机厅功能添加")
    else:
        await go_on.finish("本群尚未开通排卡功能，请联系群主或管理员添加群聊")


@get_run.handle()
async def handle_function(bot: Bot, event: GroupMessageEvent):
    global data_json
    group_id = str(event.group_id)
    user_id = str(event.get_user_id())
    nickname = event.sender.nickname
    if group_id in data_json:
        if data_json[group_id] == {}:
            await get_run.finish('本群没有机厅')
        for n in data_json[group_id]:
            if nickname in data_json[group_id][n]['list']:
                msg = nickname + "从" + str(n) + "退勤成功"
                data_json[group_id][n]['list'].remove(nickname)
                await re_write_json()
                await go_on.finish(MessageSegment.text(msg))
        await go_on.finish(f"今晚被白丝小萝莉魅魔榨精（您未加入排卡）")
    else:
        await go_on.finish(f"本群尚未开通排卡功能,请联系群主或管理员添加群聊")


@show_list.handle()
async def handle_function(bot: Bot, event: GroupMessageEvent, name_: Message = CommandArg()):
    global data_json

    name = str(name_)
    group_id = str(event.group_id)

    if group_id in data_json:
        found = False
        target_room = None

        for room_name, room_data in data_json[group_id].items():
            if room_name == name:
                found = True
                target_room = room_name
                break
            elif 'alias_list' in room_data and name in room_data['alias_list']:
                found = True
                target_room = room_name
                break

        if found:
            msg = f"{target_room}机厅排卡如下：\n"
            num = 0
            for guest in data_json[group_id][target_room]['list']:
                msg += f"第{num + 1}位：{guest}\n"
                num += 1
            await go_on.finish(MessageSegment.text(msg))
        elif not name:
            await go_on.finish("请输入机厅名称")
        else:
            await go_on.finish("没有该机厅，若需要可使用添加机厅功能")
    else:
        await go_on.finish("本群尚未开通排卡功能，请联系群主或管理员添加群聊")


@shut_down.handle()
async def handle_function(bot: Bot, event: GroupMessageEvent, name_: Message = CommandArg()):
    global data_json

    group_id = str(event.group_id)
    name = str(name_)

    if group_id in data_json:
        if not is_superuser_or_admin(event):
            await go_on.finish("只有管理员能够闭店")

        found = False
        target_room = None

        for room_name, room_data in data_json[group_id].items():
            if room_name == name:
                found = True
                target_room = room_name
                break
            elif 'alias_list' in room_data and name in room_data['alias_list']:
                found = True
                target_room = room_name
                break

        if found:
            data_json[group_id][target_room]['list'].clear()
            await re_write_json()
            await go_on.finish(f"闭店成功，当前排卡零人")
        elif not name:
            await go_on.finish("请输入机厅名称")
        else:
            await go_on.finish("没有该机厅，若需要可使用添加机厅功能")
    else:
        await go_on.finish("本群尚未开通排卡功能，请联系群主或管理员添加群聊")


@add_group.handle()
async def handle_function(bot: Bot, event: GroupMessageEvent):
    # group_members=await bot.get_group_member_list(group_id=event.group_id)
    # for m in group_members:
    #    if m['user_id'] == event.user_id:
    #        break
    # su=get_driver().config.superusers
    # if str(event.get_user_id()) != '12345678' or str(event.get_user_id()) != '2330370458':
    #   if m['role'] != 'owner' and m['role'] != 'admin' and str(m['user_id']) not in su:
    #        await add_group.finish("只有管理员对排卡功能进行设置")
    if not is_superuser_or_admin(event):
        await go_on.finish(f"只有管理员能够添加群聊")

    global data_json
    group_id = str(event.group_id)
    if group_id in data_json:
        await go_on.finish(f"当前群聊已在名单中")
    else:
        data_json[group_id] = {}
        await re_write_json()
        await go_on.finish(f"已添加当前群聊到名单中")


@delete_group.handle()
async def handle_delete_group(bot: Bot, event: GroupMessageEvent, state: T_State):
    if not is_superuser_or_admin(event):
        await delete_group.finish("只有管理员能够删除群聊")

    global data_json
    group_id = str(event.group_id)
    if group_id not in data_json:
        await delete_group.finish("当前群聊不在名单中，无法删除")
    else:
        data_json.pop(group_id)
        await re_write_json()
        await delete_group.finish(f"已从名单中删除当前群聊")


@add_arcade.handle()
async def handle_function(bot: Bot, event: GroupMessageEvent, name_: Message = CommandArg()):
    global data_json
    name = str(name_)
    group_id = str(event.group_id)
    if group_id in data_json:
        if not is_superuser_or_admin(event):
            await go_on.finish(f"只有管理员能够添加机厅")
        if not name:
            await add_arcade.finish(f"请输入机厅名称")
        elif name in data_json[group_id]:
            await add_arcade.finish(f"机厅已在群聊中")
        else:
            tmp = {"list": []}
            data_json[group_id][name] = tmp
            await re_write_json()
            await add_arcade.finish(f"已添加当前机厅到群聊名单中")
    else:
        await add_arcade.finish(f"本群尚未开通排卡功能,请联系群主或管理员添加群聊")


@delete_arcade.handle()
async def handle_function(bot: Bot, event: GroupMessageEvent, name_: Message = CommandArg()):
    global data_json
    name = str(name_)
    group_id = str(event.group_id)

    if group_id in data_json:
        if not is_superuser_or_admin(event):
            await delete_arcade.finish(f"只有管理员能够删除机厅")
        if not name:
            await delete_arcade.finish(f"请输入机厅名称")
        elif name not in data_json[group_id]:
            await delete_arcade.finish(f"机厅不在群聊中或为机厅别名，请先添加该机厅或使用该机厅本名")
        else:
            del data_json[group_id][name]
            await re_write_json()
            await delete_arcade.finish(f"已从群聊名单中删除机厅：{name}")
    else:
        await delete_arcade.finish(f"本群尚未开通排卡功能，请联系群主或管理员添加群聊")


@add_arcade_map.handle()
async def handle_add_arcade_map(bot: Bot, event: GroupMessageEvent):
    global data_json

    group_id = str(event.group_id)
    input_str = event.raw_message.strip()

    parts = input_str.split(maxsplit=3)
    if len(parts) != 3:
        await add_arcade_map.finish("格式错误：添加机厅地图 <机厅名称> <网址>")
        return

    _, name, url = parts

    if group_id in data_json:
        if name not in data_json[group_id]:
            await add_arcade_map.finish(f"机厅 '{name}' 不在群聊中或为机厅别名，请先添加该机厅或使用该机厅本名")
            return

        if 'map' not in data_json[group_id][name]:
            data_json[group_id][name]['map'] = []

        if url in data_json[group_id][name]['map']:
            await add_arcade_map.finish(f"网址 '{url}' 已存在于机厅地图中")
            return

        data_json[group_id][name]['map'].append(url)
        await re_write_json()

        await add_arcade_map.finish(f"已成功为 '{name}' 添加机厅地图网址 '{url}'")
    else:
        await add_arcade_map.finish("本群尚未开通排卡功能，请联系群主或管理员添加群聊")


@delete_arcade_map.handle()
async def handle_delete_arcade_map(bot: Bot, event: GroupMessageEvent):
    global data_json

    group_id = str(event.group_id)
    input_str = event.raw_message.strip()

    parts = input_str.split(maxsplit=3)
    if len(parts) != 3:
        await delete_arcade_map.finish("格式错误：删除机厅地图 <机厅名称> <网址>")
        return

    _, name, url = parts

    if group_id in data_json:
        if not is_superuser_or_admin(event):
            await delete_arcade_map.finish("只有管理员能够删除机厅地图")
            return

        if name not in data_json[group_id]:
            await delete_arcade_map.finish(f"机厅 '{name}' 不在群聊中或为机厅别名，请先添加该机厅或使用该机厅本名")
            return

        if 'map' not in data_json[group_id][name]:
            await delete_arcade_map.finish(f"机厅 '{name}' 没有添加过任何地图网址")
            return

        if url not in data_json[group_id][name]['map']:
            await delete_arcade_map.finish(f"网址 '{url}' 不在机厅地图中")
            return

        data_json[group_id][name]['map'].remove(url)

        await re_write_json()

        await delete_arcade_map.finish(f"已成功从 '{name}' 删除机厅地图网址 '{url}'")
    else:
        await delete_arcade_map.finish("本群尚未开通排卡功能，请联系群主或管理员添加群聊")


@get_arcade_map.handle()
async def handle_get_arcade_map(bot: Bot, event: GroupMessageEvent):
    global data_json

    group_id = str(event.group_id)
    input_str = event.raw_message.strip()

    parts = input_str.split(maxsplit=1)
    if len(parts) != 2:
        await get_arcade_map.finish("格式错误：机厅地图 <机厅名称>")
        return

    _, query_name = parts

    if group_id in data_json:
        found = False
        for name in data_json[group_id]:
            if name == query_name or (
                    'alias_list' in data_json[group_id][name] and query_name in data_json[group_id][name][
                'alias_list']):
                found = True
                if 'map' in data_json[group_id][name] and data_json[group_id][name]['map']:
                    maps = data_json[group_id][name]['map']
                    reply = f"机厅 '{name}' 的音游地图网址如下：\n"
                    for index, url in enumerate(maps, start=1):
                        reply += f"{index}. {url}\n"
                    await get_arcade_map.finish(reply.strip())
                else:
                    await get_arcade_map.finish(f"机厅 '{name}' 尚未添加地图网址")
                break

        if not found:
            await get_arcade_map.finish(f"找不到机厅或机厅别名为 '{query_name}' 的相关信息")
    else:
        await get_arcade_map.finish("本群尚未开通排卡功能，请联系群主或管理员")


@show_arcade.handle()
async def handle_function(bot: Bot, event: GroupMessageEvent):
    global data_json
    group_id = str(event.group_id)
    if group_id in data_json:
        msg = "机厅列表如下：\n"
        num = 0
        for n in data_json[group_id]:
            msg = msg + str(num + 1) + "：" + n + "\n"
            num = num + 1
        await go_on.finish(MessageSegment.text(msg.rstrip('\n')))
    else:
        await go_on.finish(f"本群尚未开通排卡功能,请联系群主或管理员添加群聊")


@put_off.handle()
async def handle_function(bot: Bot, event: GroupMessageEvent):
    global data_json
    group_id = str(event.group_id)
    user_id = str(event.get_user_id())
    nickname = event.sender.nickname
    if group_id in data_json:
        num = 0
        for n in data_json[group_id]:
            if nickname in data_json[group_id][n]['list']:
                group_list = data_json[group_id][n]['list']
                if num + 1 != len(group_list):
                    msg = "收到，已将" + str(n) + "机厅中" + group_list[num] + "与" + group_list[num + 1] + "调换位置"
                    tmp_name = [nickname]
                    data_json[group_id][n]['list'][num], data_json[group_id][n]['list'][num + 1] = \
                    data_json[group_id][n]['list'][num + 1], data_json[group_id][n]['list'][num]
                    await re_write_json()
                    await go_on.finish(MessageSegment.text(msg))
                else:
                    await go_on.finish(f"您无需延后")
            num = num + 1
        await go_on.finish(f"您尚未排卡")
    else:
        await go_on.finish(f"本群尚未开通排卡功能,请联系群主或管理员添加群聊")


async def re_write_json():
    global data_json
    with open(arcade_data_file, 'w', encoding='utf-8') as f:
        json.dump(data_json, f, indent=4, ensure_ascii=False)


async def call_discover(lat: float, lon: float, radius: int = 10, name: str = None):
    BASE_HOST = "nearcade.phizone.cn"
    conn = http.client.HTTPSConnection(BASE_HOST)
    params = {
        "latitude": str(lat),
        "longitude": str(lon),
        "radius": str(radius),
    }
    if name:
        params["name"] = name
    query = urllib.parse.urlencode(params, safe="")
    path = f"/api/discover?{query}"
    conn.request("GET", path)
    resp = conn.getresponse()
    data = resp.read().decode("utf-8")
    conn.close()
    return json.loads(data), f"https://{BASE_HOST}/discover?{query}"  # 返回 JSON + 网页 URL

    return json.loads(data)


@location_listener.handle()
async def _(event: MessageEvent):
    for seg in event.message:
        if seg.type == "json":
            try:
                # 解析 CQ:json 的 data
                cq_data = json.loads(seg.data["data"])
                location = cq_data.get("meta", {}).get("Location.Search", {})

                lat = float(location.get("lat", 0))
                lon = float(location.get("lng", 0))
                title = location.get("name", "未知位置")

                if not lat or not lon:
                    raise Exception("<UNK>")

                result, web_url = await call_discover(lat, lon, radius=10, name=title)

                shops = result.get("shops", [])
                if not shops:
                    await location_listener.finish(f"附近没有找到机厅\n👉 详情可查看：{web_url}")
                    return

                reply_lines = []
                for shop in shops[:3]:  # 只展示 3 个，避免刷屏
                    name = shop.get("name", "未知机厅")
                    dist_val = shop.get("distance", 0)
                    dist_str = f"{dist_val * 1000:.0f}米" if isinstance(dist_val, (int, float)) else "未知距离"
                    shop_addr = shop.get("address", {}).get("detailed", "")
                    reply_lines.append(f"🎮 {name}（{dist_str}）\n📍 {shop_addr}")

                reply = "\n\n".join(reply_lines) + f"\n\n👉 更多详情请点开：{web_url}"
                await location_listener.finish(reply)

            except Exception as e:
                raise
