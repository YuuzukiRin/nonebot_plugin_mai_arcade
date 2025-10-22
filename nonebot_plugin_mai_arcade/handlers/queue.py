"""
排卡功能模块
"""

from datetime import datetime
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageSegment
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER

from ..config import data_json, re_write_json
from ..utils import resolve_arcade_name, is_superuser_or_admin


go_on = on_command("上机", priority=10, block=True)
get_in = on_command("排卡", priority=10, block=True)
get_run = on_command("退勤", priority=10, block=True)
show_list = on_command("排卡现状", priority=10, block=True)
put_off = on_command("延后", priority=10, block=True)
shut_down = on_command("闭店", priority=10, block=True)


@go_on.handle()
async def handle_go_on(bot: Bot, event: GroupMessageEvent):
    """上机 - 将当前第一位排队的移至最后"""
    global data_json
    group_id = str(event.group_id)
    user_id = str(event.get_user_id())
    nickname = event.sender.nickname
    
    if group_id in data_json:
        for n in data_json[group_id]:
            if nickname in data_json[group_id][n]['list']:
                group_list = data_json[group_id][n]['list']
                if (len(group_list) > 1 and nickname == group_list[0]):
                    msg = "收到，已将" + str(n) + "机厅中" + group_list[0] + "移至最后一位,下一位上机的是" + group_list[1] + ",当前一共有" + str(len(group_list)) + "人"
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
async def handle_get_in(bot: Bot, event: GroupMessageEvent, name_: Message = CommandArg()):
    """排卡 - 加入排队队列"""
    global data_json

    name = str(name_)
    group_id = str(event.group_id)
    user_id = str(event.get_user_id())
    nickname = event.sender.nickname

    if group_id in data_json:
        for n in data_json[group_id]:
            if nickname in data_json[group_id][n]['list']:
                await get_in.finish(f"您已加入或正在其他机厅排卡")

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
            await get_in.finish(MessageSegment.text(msg))
        elif not name:
            await get_in.finish("请输入机厅名称")
        else:
            await get_in.finish("没有该机厅，请使用添加机厅功能添加")
    else:
        await get_in.finish("本群尚未开通排卡功能，请联系群主或管理员添加群聊")


@get_run.handle()
async def handle_get_run(bot: Bot, event: GroupMessageEvent):
    """退勤 - 从排队队列中退出"""
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
                await get_run.finish(MessageSegment.text(msg))
        await get_run.finish(f"今晚被白丝小萝莉魅魔榨精（您未加入排卡）")
    else:
        await get_run.finish(f"本群尚未开通排卡功能,请联系群主或管理员添加群聊")


@show_list.handle()
async def handle_show_list(bot: Bot, event: GroupMessageEvent, name_: Message = CommandArg()):
    """排卡现状 - 展示当前排队队列的情况"""
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
            await show_list.finish(MessageSegment.text(msg))
        elif not name:
            await show_list.finish("请输入机厅名称")
        else:
            await show_list.finish("没有该机厅，若需要可使用添加机厅功能")
    else:
        await show_list.finish("本群尚未开通排卡功能，请联系群主或管理员添加群聊")


@put_off.handle()
async def handle_put_off(bot: Bot, event: GroupMessageEvent):
    """延后 - 将自己延后一位"""
    global data_json
    group_id = str(event.group_id)
    user_id = str(event.get_user_id())
    nickname = event.sender.nickname
    
    if group_id in data_json:
        for n in data_json[group_id]:
            if nickname in data_json[group_id][n]['list']:
                group_list = data_json[group_id][n]['list']
                # 找到用户在队列中的位置
                user_index = group_list.index(nickname)
                if user_index + 1 < len(group_list):
                    msg = "收到，已将" + str(n) + "机厅中" + group_list[user_index] + "与" + group_list[user_index + 1] + "调换位置"
                    # 交换位置
                    data_json[group_id][n]['list'][user_index], data_json[group_id][n]['list'][user_index + 1] = \
                        data_json[group_id][n]['list'][user_index + 1], data_json[group_id][n]['list'][user_index]
                    await re_write_json()
                    await put_off.finish(MessageSegment.text(msg))
                else:
                    await put_off.finish(f"您无需延后")
        await put_off.finish(f"您尚未排卡")
    else:
        await put_off.finish(f"本群尚未开通排卡功能,请联系群主或管理员添加群聊")


@shut_down.handle()
async def handle_shut_down(bot: Bot, event: GroupMessageEvent, name_: Message = CommandArg()):
    """闭店 - (管理)清空排队队列"""
    global data_json

    group_id = str(event.group_id)
    name = str(name_)

    if group_id in data_json:
        if not await is_superuser_or_admin(bot, event):
            await shut_down.finish("只有管理员能够闭店")

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
            await shut_down.finish(f"闭店成功，当前排卡零人")
        elif not name:
            await shut_down.finish("请输入机厅名称")
        else:
            await shut_down.finish("没有该机厅，若需要可使用添加机厅功能")
    else:
        await shut_down.finish("本群尚未开通排卡功能，请联系群主或管理员添加群聊")