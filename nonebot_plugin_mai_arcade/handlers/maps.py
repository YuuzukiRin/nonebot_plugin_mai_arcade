"""
地图管理模块
"""

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message
from nonebot.params import CommandArg, T_State
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER

from ..config import data_json, re_write_json
from ..utils import resolve_arcade_name, resolve_map_by_index, is_superuser_or_admin


add_arcade_map = on_command("添加机厅地图", priority=10, block=True)
delete_arcade_map = on_command("删除机厅地图", aliases={"移除机厅地图"}, priority=10, block=True)
get_arcade_map = on_command("机厅地图", aliases={"音游地图"}, priority=10, block=True)


@add_arcade_map.handle()
async def handle_add_arcade_map(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """添加机厅地图 - 为指定机厅添加地图网址"""
    global data_json

    group_id = str(event.group_id)
    
    # 获取命令参数
    args_text = args.extract_plain_text().strip()
    if not args_text:
        await add_arcade_map.finish("格式错误：添加机厅地图 <机厅名称/序号> <网址>")
        return
    
    parts = args_text.split(maxsplit=1)
    if len(parts) != 2:
        await add_arcade_map.finish("格式错误：添加机厅地图 <机厅名称/序号> <网址>")
        return
    
    name, url = parts
    
    if group_id not in data_json:
        await add_arcade_map.finish("本群尚未开通排卡功能，请联系群主或管理员添加群聊")
        return

    # 解析机厅名称（支持序号）
    resolved_name = resolve_arcade_name(name, group_id)
    
    if resolved_name not in data_json[group_id]:
        await add_arcade_map.finish(f"机厅 '{name}' 不在群聊中或为机厅别名，请先添加该机厅或使用该机厅本名")
        return

    if 'map' not in data_json[group_id][resolved_name]:
        data_json[group_id][resolved_name]['map'] = []

    if url in data_json[group_id][resolved_name]['map']:
        await add_arcade_map.finish(f"网址 '{url}' 已存在于机厅地图中")
        return

    data_json[group_id][resolved_name]['map'].append(url)
    await re_write_json()

    await add_arcade_map.finish(f"已成功为 '{resolved_name}' 添加机厅地图网址 '{url}'")


@delete_arcade_map.handle()
async def handle_delete_arcade_map(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """删除机厅地图 - 从指定机厅删除地图网址"""
    global data_json

    group_id = str(event.group_id)
    
    # 获取命令参数
    args_text = args.extract_plain_text().strip()
    if not args_text:
        await delete_arcade_map.finish("格式错误：删除机厅地图 <机厅名称/序号> <网址/序号>")
        return
    
    parts = args_text.split(maxsplit=1)
    if len(parts) != 2:
        await delete_arcade_map.finish("格式错误：删除机厅地图 <机厅名称/序号> <网址/序号>")
        return
    
    name, url = parts
    
    if group_id not in data_json:
        await delete_arcade_map.finish("本群尚未开通排卡功能，请联系群主或管理员添加群聊")
        return

    if not await is_superuser_or_admin(bot, event):
        await delete_arcade_map.finish("只有管理员能够删除机厅地图")
        return

    # 解析机厅名称（支持序号）
    resolved_name = resolve_arcade_name(name, group_id)

    if resolved_name not in data_json[group_id]:
        await delete_arcade_map.finish(f"机厅 '{name}' 不在群聊中或为机厅别名，请先添加该机厅或使用该机厅本名")
        return

    if 'map' not in data_json[group_id][resolved_name]:
        await delete_arcade_map.finish(f"机厅 '{resolved_name}' 没有添加过任何地图网址")
        return

    # 解析地图URL（支持序号）
    resolved_url = resolve_map_by_index(resolved_name, url, group_id)

    if resolved_url not in data_json[group_id][resolved_name]['map']:
        await delete_arcade_map.finish(f"网址 '{url}' 不在机厅地图中")
        return

    data_json[group_id][resolved_name]['map'].remove(resolved_url)

    await re_write_json()

    await delete_arcade_map.finish(f"已成功从 '{resolved_name}' 删除机厅地图网址 '{resolved_url}'")


@get_arcade_map.handle()
async def handle_get_arcade_map(bot: Bot, event: GroupMessageEvent, state: T_State, args: Message = CommandArg()):
    """查询机厅地图 - 显示指定机厅的所有地图网址"""
    global data_json

    group_id = str(event.group_id)
    
    # 获取命令参数
    args_text = args.extract_plain_text().strip()
    if not args_text:
        state["waiting_for_name"] = True
        await get_arcade_map.pause("请输入要查询地图的机厅名称/序号：")
        return
    
    await process_get_arcade_map(args_text, group_id)


@get_arcade_map.got("waiting_for_name")
async def got_arcade_map_name(bot: Bot, event: GroupMessageEvent, state: T_State):
    """获取机厅名称输入"""
    query_name = str(event.get_message()).strip()
    group_id = str(event.group_id)
    
    await process_get_arcade_map(query_name, group_id)


async def process_get_arcade_map(query_name: str, group_id: str):
    """处理查询机厅地图的逻辑"""
    global data_json

    if group_id not in data_json:
        await get_arcade_map.finish("本群尚未开通排卡功能，请联系群主或管理员")
        return

    # 解析机厅名称（支持序号）
    resolved_name = resolve_arcade_name(query_name, group_id)
    
    found = False
    for name in data_json[group_id]:
        if name == resolved_name or (
                'alias_list' in data_json[group_id][name] and resolved_name in data_json[group_id][name]['alias_list']):
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