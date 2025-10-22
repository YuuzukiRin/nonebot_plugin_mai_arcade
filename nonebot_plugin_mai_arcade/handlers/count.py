"""
人数管理模块
"""

import re
import json
import math
import datetime
import http.client

from nonebot import on_regex, on_command, on_endswith
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment, Event
from nonebot.params import T_State

from ..config import data_json, re_write_json, block_group


sv_arcade = on_regex(r"^([\u4e00-\u9fa5\w]+)\s*(==\d+|={1}\d+|\+\+\d+|--\d+|\+\+|--|[+-]?\d+)?$", priority=100)
sv_arcade_on_fullmatch = on_endswith(("几", "几人", "j"), ignorecase=False, priority=100)


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
        shop_id = re.search(r'/(\d+)/?$', arcade_data['map'][0]).group(1)
    except KeyError:
        await sv_arcade.finish(f"[{name}] 当前人数更新为 {new_num}\n由 {event.sender.nickname} 于 {current_time} 更新")

    shop_id = re.search(r'/(\d+)/?$', arcade_data['map'][0]).group(1)
    conn = http.client.HTTPSConnection("nearcade.phizone.cn")
    conn.request("GET", f"/api/shops/bemanicn/{shop_id}/attendance")
    res = conn.getresponse()
    if res.status != 200:
        await sv_arcade.send(f"获取 shop {shop_id} 云端出勤人数失败: {res.status}")
    else:
        raw_data = res.read().decode("utf-8")
        data = json.loads(raw_data)
        regnum = data["total"]
        if regnum == current_num:
            if group_id in block_group:
                return
        else:
            cha = regnum - current_num
            new_num = cha + new_num
            num_list.clear()
            num_list.append(new_num)
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

    # 使用on_endswith后，直接提取机厅名称部分
    if input_str.endswith("几人"):
        name_part = input_str[:-2].strip()
    elif input_str.endswith("几"):
        name_part = input_str[:-1].strip()
    elif input_str.endswith("j"):
        name_part = input_str[:-1].strip()
    else:
        return

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
                shop_id = re.search(r'/(\d+)/?$', arcade_info['map'][0]).group(1)
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
                        if arcade_info.get("alias_list"):
                            jtname = arcade_info["alias_list"][0]
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
                    coutnum = arcade_info.get("coutnum", 1)
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
                    coutnum = arcade_info.get("coutnum", 1)
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