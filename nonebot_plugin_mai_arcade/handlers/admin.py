"""
管理员功能模块
"""
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment, Message
from nonebot.params import T_State, EventMessage
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER

from ..config import data_json, re_write_json, block_group
from ..utils import is_superuser_or_admin


add_group = on_command("添加群聊", priority=10, block=True)
delete_group = on_command("删除群聊", priority=10, block=True)
blockgroup = on_command("静默监听模式", aliases={"静默模式", "监听模式"}, permission=SUPERUSER, priority=10, block=True)
blockdetelgroup = on_command("关闭静默监听模式", aliases={"关闭静默模式", "关闭监听模式"}, permission=SUPERUSER, priority=10, block=True)


@add_group.handle()
async def handle_add_group(bot: Bot, event: GroupMessageEvent):
    """添加群聊 - 将当前群聊添加到排卡功能的群聊名单中"""
    if not await is_superuser_or_admin(bot, event):
        await add_group.finish("只有管理员能够添加群聊")

    global data_json
    group_id = str(event.group_id)
    if group_id in data_json:
        await add_group.finish("当前群聊已在名单中")
    else:
        data_json[group_id] = {}
        await re_write_json()
        await add_group.finish("已添加当前群聊到名单中")


@delete_group.handle()
async def handle_delete_group(bot: Bot, event: GroupMessageEvent, state: T_State):
    """删除群聊 - 将当前群聊从排卡功能的群聊名单中移除"""
    if not await is_superuser_or_admin(bot, event):
        await delete_group.finish("只有管理员能够删除群聊")

    global data_json
    group_id = str(event.group_id)
    if group_id not in data_json:
        await delete_group.finish("当前群聊不在名单中，无法删除")
    else:
        data_json.pop(group_id)
        await re_write_json()
        await delete_group.finish("已从名单中删除当前群聊")


@blockgroup.handle()
async def handle_blockgroup(bot: Bot, event: GroupMessageEvent):
    """静默监听模式"""
    group_id = str(event.group_id)
    block_group.add(group_id)
    await blockgroup.finish(f"已将{group_id}加入BlockGroup List，进行静默监听模式")


@blockdetelgroup.handle()
async def handle_blockdetelgroup(bot: Bot, event: GroupMessageEvent):
    """关闭静默监听模式"""
    group_id = str(event.group_id)
    block_group.discard(group_id)
    await blockdetelgroup.finish(f"已将{group_id}从BlockGroup List删除，改为正常模式")