<div align="center">
  <!-- 
  <a href="https://v2.nonebot.dev/store"><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="./docs/yuuzuki_join_s.gif" width="240" alt="NoneBotPluginText"></p>
  -->
  <a href="https://v2.nonebot.dev/store"><img src="./docs/NoneBotPlugin.svg" width="300" alt="logo"></a>
</div>

<div align="center">
  
# nonebot-plugin-mai-arcade

_✨ NoneBot2 插件 用于为maimai玩家提供机厅人数上报、排卡功能支持 ✨_

<a href="./LICENSE">
</a>
<img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="python">
</div>

## 📖 介绍

nonebot-plugin-mai-arcade 是一个基于本地数据的多功能机厅排卡报数插件，旨在为群聊舞萌玩家提供汇报机厅人数及线上排卡支持。该插件能够实现机厅人数上报，机厅排卡，添加机厅地图、别名，机厅状态管理和实时更新机厅人数状态等功能。
### 实现功能

- [x]  上报机厅人数
- [x]  显示当日更新过人数的机厅信息
- [x]  显示最新上报用户名及上报时间
- [x]  添加机厅别名
- [x]  显示机厅别名
- [x]  添加机厅音游地图网址
- [x]  显示群聊机厅地图列表
- [x]  实现线上排卡功能
- [x]  指定机厅排卡
- [ ]  随个机厅出勤
- [ ]  平均等待时间
### 功能优势

- 查询机厅人数显示最新上报用户及上报时间, 保证人数信息的实时性。
- 使用 mai/机厅人数 指令能显示当日更新过人数的机厅列表(人数及上报用户、时间), 帮助群友选择出勤地点。
- 使用 机厅地图 指令可上传、查看相应机厅音游地图网址, 便于快速查看机厅信息。
## 💿 安装

<details open>
<summary>直接下载</summary> 
下载文件，将nonebot_plugin_mai_arcade文件夹放入您的nonebot2插件目录内(通常位于 : 您的插件根目录\src\plugins)
</details>

<details open>
<summary>使用 nb-cli 安装</summary> 
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-mai-arcade

</details>

<details>
<summary>使用包管理器安装</summary> 
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary> 

    pip install nonebot-plugin-mai-arcade

</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_mai_arcade"]

</details>

## 🎉 使用
使用 `机厅帮助/arcade help` 指令获取指令表
### 指令表
| 人数指令 | 权限 | 需要@ | 范围 | 说明 |
|:-----:|:----:|:----:|:----:|:----:|
| <机厅名>++/-- | 群员 | 否 | 群聊 | 机厅的人数+1/-1 |
| <机厅名>+num/-num | 群员 | 否 | 群聊 | +num/-num |
| <机厅名>=num/<机厅名>num| 群员 | 否 | 群聊 | 机厅的人数重置为num |
| <机厅名>几/几人/j | 群员 | 否 | 群聊 | 展示机厅当前的人数信息 |
| mai/机厅人数 | 群员 | 否 | 群聊 | 展示当日已更新的所有机厅的人数列表 |

| 机厅指令 | 权限 | 需要@ | 范围 | 说明 |
|:-----:|:----:|:----:|:----:|:----:|
| 添加群聊 | 管理 | 否 | 群聊 | 将群聊添加到JSON数据中 |
| 删除群聊 | 管理 | 否 | 群聊 | 从JSON数据中删除指定的群聊 |
| 添加机厅 | 管理 | 否 | 群聊 | 将机厅添加到群聊 |
| 删除机厅 | 管理 | 否 | 群聊 | 从群聊中删除指定的机厅 |
| 机厅列表 | 群员 | 否 | 群聊 | 展示当前机厅列表 |
| 添加机厅别名 | 管理 | 否 | 群聊 | 为机厅添加别名 |
| 删除机厅别名 | 管理 | 否 | 群聊 | 移除机厅的别名 |
| 机厅别名 | 群员 | 否 | 群聊 | 展示机厅别名 |
| 添加机厅地图 | 管理 | 否 | 群聊 | 添加机厅地图信息(网址) |
| 删除机厅地图 | 管理 | 否 | 群聊 | 移除机厅地图信息 |
| 机厅地图 | 群员 | 否 | 群聊 | 展示机厅音游地图列表 |

| 排卡指令 | 权限 | 需要@ | 范围 | 说明 |
|:-----:|:----:|:----:|:----:|:----:|
| 排卡 | 群员 | 否 | 群聊 | 加入排队队列 |
| 上机 | 群员 | 否 | 群聊 | 将当前第一位排队的移至最后 |
| 退勤 | 群员 | 否 | 群聊 | 从排队队列中退出 |
| 排卡现状 | 群员 | 否 | 群聊 | 展示当前排队队列的情况 |
| 延后 | 群员 | 否 | 群聊 | 将自己延后一位 |
| 闭店 | 管理 | 否 | 群聊 | 清空排队队列 |

### 效果图

<details>
<summary>展开</summary>

![image](https://github.com/YuuzukiRin/nonebot_plugin_mai_arcade/blob/main/docs/add_group_chat.png)
![image](https://github.com/YuuzukiRin/nonebot_plugin_mai_arcade/blob/main/docs/arcade_number_reported.png)
![image](https://github.com/YuuzukiRin/nonebot_plugin_mai_arcade/blob/main/docs/arcade_number_inquiry.png)
![image](https://github.com/YuuzukiRin/nonebot_plugin_mai_arcade/blob/main/docs/add_alias_map.png)
![image](https://github.com/YuuzukiRin/nonebot_plugin_mai_arcade/blob/main/docs/arcade_queue_card.png)

</details>

## ✨ 特别感谢
- [Yzfoil/nonebot_plugin_maimai_go_down_system](https://github.com/Yzfoil/nonebot_plugin_maimai_go_down_system) 提供的灵感与代码支持
