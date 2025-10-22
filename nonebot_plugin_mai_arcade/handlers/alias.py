"""
别名管理处模块
"""

from datetime import datetime

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message
from nonebot.params import CommandArg, T_State
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER

from ..config import data_json, re_write_json
from ..utils import resolve_arcade_name, resolve_alias_by_index, is_superuser_or_admin


add_alias = on_command("添加机厅别名", priority=10, block=True)
delete_alias = on_command("删除机厅别名", aliases={"移除机厅别名"}, priority=10, block=True)
get_arcade_alias = on_command("机厅别名", priority=10, block=True)


@add_alias.handle()
async def handle_add_alias(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """添加机厅别名 - 为指定机厅添加新的别名"""
    global data_json

    group_id = str(event.group_id)
    
    # 获取命令参数
    args_text = args.extract_plain_text().strip()
    if not args_text:
        await add_alias.finish("格式错误：添加机厅别名 <店名/序号> <别名>")
        return

    parts = args_text.split(maxsplit=1)
    if len(parts) != 2:
        await add_alias.finish("格式错误：添加机厅别名 <店名/序号> <别名>")
        return

    name, alias = parts

    if group_id not in data_json:
        await add_alias.finish("本群尚未开通排卡功能，请联系群主或管理员添加群聊")
        return

    if not await is_superuser_or_admin(bot, event):
        await add_alias.finish("只有管理员能够添加机厅别名")
        return

    # 解析机厅名称（支持序号）
    resolved_name = resolve_arcade_name(name, group_id)

    if resolved_name not in data_json[group_id]:
        await add_alias.finish(f"店名 '{name}' 不在群聊中或为机厅别名，请先添加该机厅或使用该机厅本名")
        return

    if alias in data_json[group_id][resolved_name].get("alias_list", []):
        await add_alias.finish(f"别名 '{alias}' 已存在，请使用其他别名")
        return

    # 添加别名到指定机厅
    alias_list = data_json[group_id][resolved_name].get("alias_list", [])
    alias_list.append(alias)
    data_json[group_id][resolved_name]["alias_list"] = alias_list

    await re_write_json()

    await add_alias.finish(f"已成功为 '{resolved_name}' 添加别名 '{alias}'")


@delete_alias.handle()
async def handle_delete_alias(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """删除机厅别名 - 删除指定机厅的别名"""
    global data_json

    group_id = str(event.group_id)
    
    # 获取命令参数
    args_text = args.extract_plain_text().strip()
    if not args_text:
        await delete_alias.finish("格式错误：删除机厅别名 <店名/序号> <别名/序号>")
        return

    parts = args_text.split(maxsplit=1)
    if len(parts) != 2:
        await delete_alias.finish("格式错误：删除机厅别名 <店名/序号> <别名/序号>")
        return

    name, alias = parts

    if group_id not in data_json:
        await delete_alias.finish("本群尚未开通排卡功能，请联系群主或管理员添加群聊")
        return

    if not await is_superuser_or_admin(bot, event):
        await delete_alias.finish("只有管理员能够删除机厅别名")
        return

    # 解析机厅名称（支持序号）
    resolved_name = resolve_arcade_name(name, group_id)

    if resolved_name not in data_json[group_id]:
        await delete_alias.finish(f"店名 '{name}' 不在群聊中或为机厅别名，请先添加该机厅或使用该机厅本名")
        return

    # 解析别名（支持序号）
    resolved_alias = resolve_alias_by_index(resolved_name, alias, group_id)

    alias_list = data_json[group_id][resolved_name].get("alias_list", [])
    if resolved_alias not in alias_list:
        await delete_alias.finish(f"别名 '{alias}' 不存在，请检查输入的别名")
        return

    alias_list.remove(resolved_alias)
    data_json[group_id][resolved_name]["alias_list"] = alias_list

    await re_write_json()

    await delete_alias.finish(f"已成功删除 '{resolved_name}' 的别名 '{resolved_alias}'")


@get_arcade_alias.handle()
async def handle_get_arcade_alias(bot: Bot, event: GroupMessageEvent, state: T_State, args: Message = CommandArg()):
    """查询机厅别名 - 查看指定机厅的所有别名"""
    global data_json

    group_id = str(event.group_id)
    
    # 获取命令参数
    args_text = args.extract_plain_text().strip()
    if not args_text:
        state["waiting_for_name"] = True
        await get_arcade_alias.pause("请输入要查询别名的机厅名称/序号：")
        return
    
    await process_get_arcade_alias(args_text, group_id)


@get_arcade_alias.got("waiting_for_name")
async def got_arcade_alias_name(bot: Bot, event: GroupMessageEvent, state: T_State):
    """获取用户输入的机厅名称并处理查询"""
    query_name = str(event.get_message()).strip()
    group_id = str(event.group_id)
    
    await process_get_arcade_alias(query_name, group_id)


async def process_get_arcade_alias(query_name: str, group_id: str):
    """处理查询机厅别名的核心逻辑"""
    global data_json
 
    if group_id not in data_json:
        await get_arcade_alias.finish("本群尚未开通相关功能，请联系群主或管理员添加群聊")
        return

    # 解析机厅名称（支持序号）
    resolved_name = resolve_arcade_name(query_name, group_id)
    
    found = False
    for name in data_json[group_id]:
        # 检查是否匹配机厅名称或别名列表中的别名
        if name == resolved_name or (
                'alias_list' in data_json[group_id][name] and resolved_name in data_json[group_id][name]['alias_list']):
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