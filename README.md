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

_✨ NoneBot2 插件 为maimai玩家提供机厅人数上报、附近机厅查找、线上排卡、Nearcade云同步功能支持 ✨_

<a href="./LICENSE">
</a>
<img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="python">
<img src="https://img.shields.io/badge/nonebot-2.0+-red.svg" alt="nonebot">
<img src="https://img.shields.io/badge/version-0.2.0-green.svg" alt="version">
</div>

## 📖 介绍

nonebot-plugin-mai-arcade 是一款强大的基于`本地&云端数据`的多功能机厅插件，旨在为群聊舞萌玩家提供机厅人数上报、附近机厅查找、线上排卡、Nearcade云同步功能支持。本插件可实现机厅人数上报、更新，机厅信息云同步，机厅地图、别名添加，查找附近的机厅，线上排卡，机厅状态管理等功能。

### 🚀 v0.2.0 重构版本

**☁️ Nearcade云同步集成**：
- [x] **附近机厅功能**：群聊发送位置发现附近机厅
- [x] **实时数据上传**：机厅人数变更自动同步至云端
- [x] **机厅数据同步**：从云端同步实时机厅人数信息
- [x] **添加机厅检索**：支持关键词搜索平台收录机厅
- [x] **地图自动添加**：选择搜索到的机厅自动添加地图网址

**🏗️ 架构升级**：
- [x] **模块化设计**：重构单文件为模块化架构
- [x] **Bug修复**：修复命令前缀问题

### 🎯 核心功能

- [x] **机厅人数**：上报机厅人数，自动同步云端
- [x] **出勤统计**：显示当日更新过人数的机厅信息
- [x] **用户更新**：显示最新上报用户名及上报时间
- [x] **别名系统**：添加和管理机厅别名
- [x] **地图系统**：添加和管理机厅音游地图网址
- [x] **索引系统**：通过序号快捷管理机厅、别名、地图
- [x] **线上排卡**：实现线上排卡功能，指定机厅排卡
- [x] **机厅搜索**：添加时关键词搜索机厅
- [x] **附近机厅**：发送位置发现附近机厅
- [x] **平均等待时间**：根据机厅人数、机台数预测当前机厅平均等待时间，给出出勤建议
- [ ] 随个机厅出勤
- [ ] 更多机台种类

### 💡 功能说明

<details>
<summary><strong>📍 附近机厅</strong>：基于Nearcade数据库的位置服务，在群聊发送位置可发现附近机厅</summary>

![image](https://github.com/YuuzukiRin/nonebot_plugin_mai_arcade/blob/main/docs/discover_nearby_arcades.png)

</details>

<details>
<summary><strong>⏰ 实时建议</strong>：查询机厅人数显示最新上报用户及上报时间，从Nearcade同步实时人数信息，同时根据人数和机台信息给出出勤建议</summary>

![image](https://github.com/YuuzukiRin/nonebot_plugin_mai_arcade/blob/main/docs/live_suggestion.png)

</details>

<details>
<summary><strong>📊 出勤统计</strong>：使用<code>mai/机厅人数</code>指令显示当日更新过人数的机厅列表，帮助群友选择出勤地点</summary>

![image](https://github.com/YuuzukiRin/nonebot_plugin_mai_arcade/blob/main/docs/attendance_stats.png)

</details>

<details>
<summary><strong>☁️ 云端同步</strong>：每次人数更新自动上传至Nearcade云端，与平台同步实时数据</summary>

![image](https://github.com/YuuzukiRin/nonebot_plugin_mai_arcade/blob/main/docs/sync_to_cloud.png)

</details>

<details>
<summary><strong>🔍 机厅检索</strong>：集成Nearcade API，使用<code>添加机厅</code>指令时会根据关键词自动检索相关机厅，可通过序号选择添加相应机厅或操作</summary>

![image](https://github.com/YuuzukiRin/nonebot_plugin_mai_arcade/blob/main/docs/search_add_arcades.png)

</details>

<details>
<summary><strong>🔢 索引系统</strong>：使用<code>机厅列表</code>指令可查看群聊添加的机厅，可使用序号指代相应机厅名称（别名、地图同理）</summary>

![image](https://github.com/YuuzukiRin/nonebot_plugin_mai_arcade/blob/main/docs/arcade_list_manage.png)

</details>

<details>
<summary><strong>🗺️ 地图系统</strong>：使用<code>mai/（添加）机厅地图</code>指令可添加、查看指定机厅音游地图网址，支持<a href="https://nearcade.phizone.cn/">Nearcade</a>和<a href="https://map.bemanicn.com">BEMANICN全国音游地图</a>
<br><br><strong>（注意：只有添加地图网址的机厅才可以使用云端同步、实时建议功能）</strong></summary>

![image](https://github.com/YuuzukiRin/nonebot_plugin_mai_arcade/blob/main/docs/mapurl_setup.png)

</details>

## 🏗️ 项目结构

```
nonebot_plugin_mai_arcade/
├── __init__.py          # 主入口文件
├── config.py           # 配置管理
├── utils.py            # 工具函数
├── services.py         # 外部API服务
└── handlers/           # 功能模块
    ├── __init__.py
    ├── arcade.py       # 机厅管理
    ├── queue.py        # 排卡管理
    ├── alias.py        # 别名管理
    ├── maps.py         # 地图管理
    ├── count.py        # 人数统计
    └── admin.py        # 管理员功能
```

## 💿 安装

<details open>
<summary>直接下载</summary> 
clone 本项目，将nonebot_plugin_mai_arcade文件夹放入您的nonebot2插件目录内(通常位于 : 您的插件根目录\src\plugins)
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
| 添加机厅地图 | 群员 | 否 | 群聊 | 添加机厅地图信息(网址) |
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

| 位置服务 | 权限 | 需要@ | 范围 | 说明 |
|:-----:|:----:|:----:|:----:|:----:|
| 发送位置 | 群员 | 否 | 群聊 | 自动获取附近机厅信息（基于Nearcade数据库） |

| 云端同步 | 权限 | 需要@ | 范围 | 说明 |
|:-----:|:----:|:----:|:----:|:----:|
| 人数更新 | 群员 | 否 | 群聊 | 自动上传至Nearcade云端数据库 |
| 机厅搜索 | 管理 | 否 | 群聊 | 添加机厅时自动搜索Nearcade数据库 |

**索引支持**：机厅名、别名、地图URL均可用序号代替 (使用 `机厅列表` 命令查看对应序号)  
**示例**：`删除机厅别名 1 2` (删除第1个机厅的第2个别名)

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

- [Nearcade](https://nearcade.phizone.cn) 提供的优秀机厅数据平台和API支持
- [Koileo](https://github.com/Koileo) 对项目Nearcade云同步功能及诸多模块的重要贡献和支持
- [Adsicmes](https://github.com/Adsicmes) 对命令前缀问题的修复改进
- [Yzfoil/nonebot_plugin_maimai_go_down_system](https://github.com/Yzfoil/nonebot_plugin_maimai_go_down_system) 提供的灵感与代码支持

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

<div align="center">
  <p>如果这个项目对你有帮助，请给它一个 ⭐ Star！</p>
  <p>项目地址：<a href="https://github.com/YuuzukiRin/nonebot_plugin_mai_arcade">https://github.com/YuuzukiRin/nonebot_plugin_mai_arcade</a></p>
</div>
