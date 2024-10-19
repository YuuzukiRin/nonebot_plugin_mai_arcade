import re
import json
import datetime
from .config import Config
from nonebot import get_driver, require, on_endswith, on_command, on_regex, on_fullmatch
from nonebot.plugin import PluginMetadata
from nonebot.adapters import Bot, Event, Message
from nonebot.adapters.onebot.v11 import MessageSegment, GroupMessageEvent
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.rule import ArgumentParser


__plugin_meta__ = PluginMetadata(
    name="nonebot_plugin_mai_arcade",
    description="舞萌机厅插件",
    usage="",
    config=Config,
)

global_config = get_driver().config
config = Config.parse_obj(global_config)


data_json={}
data_path=r"D:\NoneBot2\yuuzuki\src\plugins\nonebot_plugin_mai_arcade\data.json"



def init_data():
    global data_json
    with open(data_path , encoding='utf-8') as f:
        data_json=json.load(f)

# 初始化和加载数据
init_data()

go_on=on_command("上机")#将当前第一位排队的移至最后
get_in=on_command("排卡")#加入排队队列
get_run=on_command("退勤")#退出排队队列
show_list=on_command("排卡现状")#展示排队队列
add_group=on_command("添加群聊")#添加群聊到json
delete_group=on_command("删除群聊")#从json删除群聊
shut_down=on_command("闭店")#清空排队队列
add_arcade=on_command("添加机厅")#添加机厅到群聊
delete_arcade=on_command("删除机厅")#删除群聊中的机厅
show_arcade=on_command("机厅列表")#展示机厅列表
put_off=on_command("延后")#将自己延后一位
add_alias=on_command("添加机厅别名")
delete_alias=on_command("删除机厅别名", aliases={"移除机厅别名"})
get_arcade_alias =on_command("机厅别名")
add_arcade_map=on_command("添加机厅地图")
delete_arcade_map=on_command("删除机厅地图", aliases={"移除机厅地图"})
get_arcade_map = on_command("机厅地图", aliases={"音游地图"})#展示机厅音游地图
sv_arcade=on_regex(r'^(?!.*[+-]\d+)(.*?)\d+$|^(.*?)[+-=]+$', priority=15)#编辑机厅人数
sv_arcade_on_fullmatch=on_endswith(("几", "几人", "j"), ignorecase=False)#展示机厅人数
query_updated_arcades=on_fullmatch(("mai", "机厅人数"), ignorecase=False)#展示机厅人数列表
scheduler = require('nonebot_plugin_apscheduler').scheduler

superusers = get_driver().config.superusers
def is_superuser_or_admin(event: GroupMessageEvent) -> bool:
    user_id = str(event.user_id)
    # 检查是否是超级用户或管理员/群主
    return event.sender.role in ["admin", "owner"] or user_id in superusers

@scheduler.scheduled_job('cron', hour=0, minute=0)
async def clear_data_daily():
    global data_json
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    for group_id, arcades in data_json.items():
        for arcade_name, info in arcades.items():
            if 'last_updated_by' in info:
                info['last_updated_by'] = None
            if 'last_updated_at' in info:
                info['last_updated_at'] = None
            if 'num' in info:
                info['num'] = []
                
    print(f"arcade缓存清理完成")    
         
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

        # 假设这里有一个异步函数来写入 JSON 数据到文件中
        await re_write_json()

        await add_alias.finish(f"已成功为 '{name}' 添加别名 '{alias}'")
    else:
        await add_alias.finish("本群尚未开通排卡功能，请联系群主或管理员")
        
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

        # Remove alias from the alias list
        alias_list.remove(alias)
        data_json[group_id][name]["alias_list"] = alias_list

        # 假设这里有一个异步函数来写入 JSON 数据到文件中
        await re_write_json()

        await delete_alias.finish(f"已成功删除 '{name}' 的别名 '{alias}'")
    else:
        await delete_alias.finish("本群尚未开通排卡功能，请联系群主或管理员")
        
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
            # 检查是否匹配机厅名称或别名列表中的别名
            if name == query_name or ('alias_list' in data_json[group_id][name] and query_name in data_json[group_id][name]['alias_list']):
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
        await get_arcade_alias.finish("本群尚未开通相关功能，请联系群主或管理员")
        
@sv_arcade.handle()
async def handle_sv_arcade(bot: Bot, event: GroupMessageEvent, state: T_State):
    global data_json

    input_str = event.raw_message.strip()
    group_id = str(event.group_id)
    current_time = datetime.datetime.now().strftime("%m-%d %H:%M")

    special_pattern = r'^(.*?)=(\d+)$|^(?!.*[+-])(.*?)\d+$'
    special_match = re.match(special_pattern, input_str)
    if special_match:
        groups = special_match.groups()
        room_name_or_alias = (groups[0] or groups[2]).strip()  # 处理两个可能的捕获组
        new_num_str = groups[1] if groups[1] is not None else re.search(r'\d+$', input_str).group()
        new_num = int(new_num_str)  # 将提取的数字字符串转换为整数

        if new_num_str is not None:
            new_num = int(new_num_str)
        else:
            new_num = 0
            
        if group_id in data_json:
            found = False
            if room_name_or_alias in data_json[group_id]:
                found = True
            else:
                for room_name, room_data in data_json[group_id].items():
                    if "alias_list" in room_data and room_name_or_alias in room_data["alias_list"]:
                        room_name_or_alias = room_name
                        found = True
                        break
            
            if found:
                data_json[group_id][room_name_or_alias]["num"] = [new_num]
                data_json[group_id][room_name_or_alias].pop("previous_update_by", None)
                data_json[group_id][room_name_or_alias].pop("previous_update_at", None)
                data_json[group_id][room_name_or_alias]["last_updated_by"] = event.sender.nickname
                data_json[group_id][room_name_or_alias]["last_updated_at"] = current_time

                await re_write_json()
                await sv_arcade.finish(f"[{room_name_or_alias}] 当前人数重置为 {new_num}\n由 {event.sender.nickname} 于 {current_time} 更新")
            else:
                return

        else:
            return
            #await sv_arcade.finish(f"群聊 '{group_id}' 中不存在任何机厅")

        return

    pattern = r'^(.*?)(\+\+|--|[+-]?\d+)$'
    match = re.match(pattern, input_str)
    if not match:
        return

    name = match.group(1).strip()
    operation = match.group(2)

    if group_id in data_json:
        found = False
        if name in data_json[group_id]:
            found = True
        else:
            for room_name, room_data in data_json[group_id].items():
                if "alias_list" in room_data and name in room_data["alias_list"]:
                    name = room_name
                    found = True
                    break
        
        if found:
            num_list = data_json[group_id][name].setdefault("num", [])

            if operation == "++":
                num_list.append(1)
            elif operation == "--":
                if num_list:
                    num_list.pop()
            else:
                delta = int(operation)
                num_list.append(delta)

            # 更新操作用户和时间，并删除之前的记录
            data_json[group_id][name]["last_updated_by"] = event.sender.nickname
            data_json[group_id][name]["last_updated_at"] = current_time
            data_json[group_id][name].pop("previous_update_by", None)
            data_json[group_id][name].pop("previous_update_at", None)

            await re_write_json()
            current_num = sum(num_list)
            await sv_arcade.finish(f"[{name}] 当前人数更新为 {current_num}\n由 {event.sender.nickname} 于 {current_time} 更新")
        else:
            return
    else:
        return
        
@sv_arcade_on_fullmatch.handle()
async def handle_sv_arcade_on_fullmatch(bot: Bot, event: Event, state: T_State):
    global data_json

    input_str = event.raw_message.strip()
    group_id = str(event.group_id)

    # 修改匹配指令格式的正则表达式
    pattern = r'^([\u4e00-\u9fa5\w]+)([几j]\d*人?)$'  # 匹配格式为中文、英文、数字等组成，末尾是几、j、几人
    match = re.match(pattern, input_str)
    if not match:
        return

    # 提取参数
    name_part = match.group(1).strip()  # 机厅名或别名部分
    num_part = match.group(2).strip()   # 几、j、几人部分

    if group_id in data_json:
        found_arcade = None

        # 首先尝试匹配机厅名
        if name_part in data_json[group_id]:
            found_arcade = name_part
        else:
            # 否则尝试匹配别名列表
            for arcade_name, arcade_info in data_json[group_id].items():
                alias_list = arcade_info.get("alias_list", [])
                if name_part in alias_list:
                    found_arcade = arcade_name
                    break
        
        if found_arcade:
            arcade_info = data_json[group_id][found_arcade]
            num_list = arcade_info.setdefault("num", [])
            
            if not num_list:  # 如果num_list为空
                await sv_arcade_on_fullmatch.finish(f"[{found_arcade}] 今日人数尚未更新")
            else:
                current_num = sum(num_list)
                
                # 获取更新者和更新时间，如果不存在则直接输出人数
                last_updated_by = arcade_info.get("last_updated_by")
                last_updated_at = arcade_info.get("last_updated_at")

                if last_updated_by and last_updated_at:
                    await sv_arcade_on_fullmatch.finish(f"[{found_arcade}] 当前人数为 {current_num}\n由 {last_updated_by} 于 {last_updated_at} 更新")
                else:
                    await sv_arcade_on_fullmatch.finish(f"[{found_arcade}] 当前人数为 {current_num}")
        else:
            await sv_arcade_on_fullmatch.finish(f"群聊 '{group_id}' 中不存在机厅或机厅别名 '{name_part}'")
    else:
        return
        #await sv_arcade_on_fullmatch.finish(f"群聊 '{group_id}' 中不存在任何机厅")
                
@query_updated_arcades.handle()
async def handle_query_updated_arcades(bot: Bot, event: Event, state: T_State):
    global data_json
    group_id = str(event.group_id)

    # 构建回复消息的列表
    reply_messages = []

    if group_id in data_json:
        for arcade_name, arcade_info in data_json[group_id].items():
            num_list = arcade_info.get("num", [])
            if num_list:
                # 检查最后更新时间是否有内容
                last_updated_at = arcade_info.get("last_updated_at")
                if last_updated_at:  # 如果有最后更新时间
                    current_num = sum(num_list)
                    last_updated_by = arcade_info.get("last_updated_by", "未知用户")
                    update_info = f" [{arcade_name}] 当前人数为 {current_num} "
                    update_info += f"\n由 {last_updated_by} 于 {last_updated_at} 更新"
                    reply_messages.append(update_info)

    if reply_messages:
        await query_updated_arcades.finish('\n'.join(reply_messages))
    else:
        await query_updated_arcades.finish("今天没有任何机厅人数被更新过")

@go_on.handle()
async def handle_function(bot:Bot,event:GroupMessageEvent):
    global data_json
    group_id=str(event.group_id)
    user_id = str(event.get_user_id())
    nickname = event.sender.nickname
    if group_id in data_json:
        for n in data_json[group_id]:
            if nickname in data_json[group_id][n]['list']:
                group_list=data_json[group_id][n]['list']
                if (len(group_list)>1 and nickname == group_list[0]) :
                    msg="收到，已将"+str(n)+"机厅中"+group_list[0]+"移至最后一位,下一位上机的是"+group_list[1]+",当前一共有"+str(len(group_list))+"人"
                    tmp_name=[nickname]
                    data_json[group_id][n]['list']=data_json[group_id][n]['list'][1:]+tmp_name
                    await re_write_json()
                    await go_on.finish(MessageSegment.text(msg))
                elif (len(group_list)==1 and nickname == group_list[0]):
                    msg="收到,"+str(n)+"机厅人数1人,您可以爽霸啦"
                    await go_on.finish(MessageSegment.text(msg))
                else:
                    await go_on.finish(f"暂时未到您,请耐心等待")
        await go_on.finish(f"您尚未排卡")
    else:
        await go_on.finish(f"本群尚未开通排卡功能,请联系群主或管理员")

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

        # 检查输入的名称是否直接是机厅名或是其别名
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
        await go_on.finish("本群尚未开通排卡功能，请联系群主或管理员")

@get_run.handle()
async def handle_function(bot:Bot,event:GroupMessageEvent):
    global data_json
    group_id=str(event.group_id)
    user_id = str(event.get_user_id())
    nickname = event.sender.nickname
    if group_id in data_json:
        if data_json[group_id] == {}:
            await get_run.finish('本群没有机厅')
        for n in data_json[group_id]:
            if nickname in data_json[group_id][n]['list']:
                msg=nickname+"从"+str(n)+"退勤成功"
                data_json[group_id][n]['list'].remove(nickname)
                await re_write_json()
                await go_on.finish(MessageSegment.text(msg))
        await go_on.finish(f"今晚被白丝小萝莉魅魔榨精（您未加入排卡）")
    else:
        await go_on.finish(f"本群尚未开通排卡功能,请联系群主或管理员")

@show_list.handle()
async def handle_function(bot: Bot, event: GroupMessageEvent, name_: Message = CommandArg()):
    global data_json

    name = str(name_)
    group_id = str(event.group_id)

    if group_id in data_json:
        found = False
        target_room = None

        # 检查输入的名称是否直接是机厅名或是其别名
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
                msg += f"第{num+1}位：{guest}\n"
                num += 1
            await go_on.finish(MessageSegment.text(msg))
        elif not name:
            await go_on.finish("请输入机厅名称")
        else:
            await go_on.finish("没有该机厅，若需要可使用添加机厅功能")
    else:
        await go_on.finish("本群尚未开通排卡功能，请联系群主或管理员")

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

        # 检查输入的名称是否直接是机厅名或是其别名
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
        await go_on.finish("本群尚未开通排卡功能，请联系群主或管理员")

@add_group.handle()
async def handle_function(bot:Bot,event:GroupMessageEvent):
    
    #group_members=await bot.get_group_member_list(group_id=event.group_id)
    #for m in group_members:
    #    if m['user_id'] == event.user_id:
    #        break
    #su=get_driver().config.superusers
    #if str(event.get_user_id()) != '347492847' or str(event.get_user_id()) != '1415279603':
    #   if m['role'] != 'owner' and m['role'] != 'admin' and str(m['user_id']) not in su:
    #        await add_group.finish("只有管理员对排卡功能进行设置")
    if not is_superuser_or_admin(event):
            await go_on.finish(f"只有管理员能够添加群聊")
    
    global data_json
    group_id=str(event.group_id)
    if group_id in data_json:
        await go_on.finish(f"当前群聊已在名单中")
    else:
        data_json[group_id]={}
        await re_write_json()
        await go_on.finish(f"已添加当前群聊到名单中")
        
@delete_group.handle()
async def handle_delete_group(bot: Bot, event: GroupMessageEvent, state: T_State):
    # 检查用户权限，只有管理员和群主可以删除群聊
    if not is_superuser_or_admin(event):
        await delete_group.finish("只有管理员能够删除群聊")

    global data_json
    group_id = str(event.group_id)
    if group_id not in data_json:
        await delete_group.finish("当前群聊不在名单中，无法删除")
    else:
        data_json.pop(group_id)
        await re_write_json()  # 保存修改后的 json 文件
        await delete_group.finish(f"已从名单中删除当前群聊")

@add_arcade.handle()
async def handle_function(bot:Bot,event:GroupMessageEvent,name_: Message = CommandArg()):
    global data_json
    name=str(name_)
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
            data_json[group_id][name]=tmp
            await re_write_json()
            await add_arcade.finish(f"已添加当前机厅到群聊名单中")
    else:
        await add_arcade.finish(f"本群尚未开通排卡功能,请联系群主或管理员")

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
        await delete_arcade.finish(f"本群尚未开通排卡功能，请联系群主或管理员")

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
        if not is_superuser_or_admin(event):
            await add_arcade_map.finish("只有管理员能够添加机厅地图")
            return
        
        if name not in data_json[group_id]:
            await add_arcade_map.finish(f"机厅 '{name}' 不在群聊中或为机厅别名，请先添加该机厅或使用该机厅本名")
            return
        
        if 'map' not in data_json[group_id][name]:
            data_json[group_id][name]['map'] = []
        
        if url in data_json[group_id][name]['map']:
            await add_arcade_map.finish(f"网址 '{url}' 已存在于机厅地图中")
            return
        
        data_json[group_id][name]['map'].append(url)
        
        # 假设这里有一个异步函数来写入 JSON 数据到文件中
        await re_write_json()
        
        await add_arcade_map.finish(f"已成功为 '{name}' 添加机厅地图网址 '{url}'")
    else:
        await add_arcade_map.finish("本群尚未开通排卡功能，请联系群主或管理员")
        
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
        
        # 假设这里有一个异步函数来写入 JSON 数据到文件中
        await re_write_json()
        
        await delete_arcade_map.finish(f"已成功从 '{name}' 删除机厅地图网址 '{url}'")
    else:
        await delete_arcade_map.finish("本群尚未开通排卡功能，请联系群主或管理员")   

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
            # 检查是否匹配机厅名称或别名列表中的别名
            if name == query_name or ('alias_list' in data_json[group_id][name] and query_name in data_json[group_id][name]['alias_list']):
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
async def handle_function(bot:Bot,event:GroupMessageEvent):
    global data_json
    group_id=str(event.group_id)
    if group_id in data_json:
        msg="机厅列表如下：\n"
        num=0
        for n in data_json[group_id]:
            msg=msg+str(num+1)+"："+n+"\n"
            num=num+1
        await go_on.finish(MessageSegment.text(msg.rstrip('\n')))
    else:
        await go_on.finish(f"本群尚未开通排卡功能,请联系群主或管理员")

@put_off.handle()
async def handle_function(bot:Bot,event:GroupMessageEvent):
    global data_json
    group_id=str(event.group_id)
    user_id = str(event.get_user_id())
    nickname = event.sender.nickname
    if group_id in data_json:
        num=0
        for n in data_json[group_id]:
            if nickname in data_json[group_id][n]['list']:
                group_list=data_json[group_id][n]['list']
                if num+1 !=len(group_list):
                    msg="收到，已将"+str(n)+"机厅中"+group_list[num]+"与"+group_list[num+1]+"调换位置"
                    tmp_name=[nickname]
                    data_json[group_id][n]['list'][num],data_json[group_id][n]['list'][num+1]=data_json[group_id][n]['list'][num+1],data_json[group_id][n]['list'][num]
                    await re_write_json()
                    await go_on.finish(MessageSegment.text(msg))
                else:
                    await go_on.finish(f"您无需延后")
            num = num + 1
        await go_on.finish(f"您尚未排卡")
    else:
        await go_on.finish(f"本群尚未开通排卡功能,请联系群主或管理员")

async def re_write_json():#复写json文档
    global data_json
    with open(data_path , 'w' , encoding='utf-8') as f:
        json.dump(data_json , f , indent=4, ensure_ascii=False)