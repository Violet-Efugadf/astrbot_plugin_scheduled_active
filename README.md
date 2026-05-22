# astrbot_plugin_scheduled_active
astrbot定时启用插件 - 仅在指定群聊的指定时间段内响应消息，其他时间完全静默，管理员可手动开关
markdown
# 📅 astrbot_plugin_scheduled_active

一个让 AstrBot 按时上下班的插件 —— 仅在指定群聊的指定时间段内响应消息，其他时间完全静默，管理员可随时手动开关。

---

## ✨ 功能特性

- 🎯 **指定群聊生效**：仅在配置的群号内激活，其他群完全无视
- ⏰ **定时上下班**：设定每日工作时段，支持跨天时段（如 22:00~06:00）
- 🔇 **完全静默模式**：非激活时段，任何消息（@、/命令、关键词唤醒、LLM 触发）都不会响应
- 🛠️ **管理员手动控制**：可随时强制开启 / 关闭 / 恢复自动模式
- 💬 **私聊白名单**：可选配置允许私聊不受时段限制
- 📊 **状态查询**：一键查看当前模式、时段、目标群聊等完整信息

---

## 📦 安装方法

### 方式一：通过插件市场（推荐）

在 AstrBot WebUI 的「插件市场」中搜索 `scheduled_active` 一键安装。

### 方式二：手动安装

```bash
cd AstrBot/data/plugins/
git clone https://github.com/yourname/astrbot_plugin_scheduled_active.git
然后在 WebUI 中重载插件即可。

目录结构
text
astrbot_plugin_scheduled_active/
├── main.py              # 插件主程序
├── metadata.yaml        # 插件元数据
├── _conf_schema.json    # 配置项定义
├── requirements.txt     # 依赖列表（无额外依赖）
└── README.md            # 本文档
⚙️ 配置说明
进入 AstrBot WebUI → 插件管理 → 找到本插件 → 点击「配置」：

配置项	类型	默认值	说明
target_groups	list	[]	目标群聊ID列表（必填），仅这些群内会响应
start_time	string	09:00	每日激活开始时间（24小时制 HH:MM）
end_time	string	22:00	每日激活结束时间（24小时制 HH:MM）
allow_private	bool	false	是否允许私聊响应（不受时段和群聊限制）
admin_ids	list	[]	管理员QQ号列表（兼容老版本，新版自动识别）
配置示例（普通时段）
json
{
    "target_groups": [123456789, 987654321],
    "start_time": "09:00",
    "end_time": "22:00",
    "allow_private": false
}
跨天时段示例（夜间工作）
json
{
    "start_time": "22:00",
    "end_time": "06:00"
}
💡 插件会自动识别跨天时段，无需额外配置。

🎮 管理员命令
以下命令任何时段均可使用（即使在静默期），且仅限管理员触发。

命令	功能描述
/active_on	🟢 强制开启机器人（覆盖定时规则）
/active_off	🔴 强制关闭机器人（覆盖定时规则）
/active_auto	🔄 恢复自动定时模式
/active_status	📊 查看当前状态详情
使用示例
查看状态：

text
/active_status
返回示例：

text
📊 机器人状态
━━━━━━━━━━━━
当前模式：自动定时模式
当前状态：✅ 激活
当前时间：14:30:25
激活时段：09:00 ~ 22:00 ✅
目标群聊：2 个
群聊列表：123456789, 987654321
临时加班：

text
/active_on
返回：✅ 已手动开启机器人（覆盖定时规则）

临时请假：

text
/active_off
返回：🔇 已手动关闭机器人（覆盖定时规则）

恢复正常排班：

text
/active_auto
返回：🔄 已恢复定时模式，当前状态：激活

🧠 工作原理
本插件利用 AstrBot 的事件钩子机制，在消息流入的最前端设置一个高优先级的「守门员」：

text
消息进入
    ↓
[守门员检查 priority=99]
    ↓
├─ 是管理员开关命令？ → 放行
├─ 是目标群聊吗？     → 否 → 🔇 拦截
├─ 在激活时段吗？     → 否 → 🔇 拦截
└─ 全部通过           → ✅ 放行给其他插件 / LLM
通过 event.stop_event() 终止事件传播，确保非激活状态下没有任何插件会被触发，实现真正的静默。

📋 常见问题 FAQ
Q1: 为什么管理员命令在静默期也能用？
守门员会优先识别管理员命令并放行，确保你能随时控制机器人。

Q2: 我想让机器人 24 小时全天工作，但只在指定群？
设置 start_time: "00:00" 和 end_time: "23:59" 即可。

Q3: 私聊会被静默吗？
默认会。如需开启私聊，将 allow_private 设为 true。

Q4: 手动开关会持久化吗？
不会。重启 AstrBot 后会自动恢复到「自动定时模式」。

Q5: 静默期间机器人能收到消息吗？
能收到，但不会有任何回应。日志中也不会触发任何插件逻辑。

Q6: 如何获取群号？
在群内发送任意消息后，查看 AstrBot 控制台日志，或使用其他插件查询 event.get_group_id()。

🛡️ 注意事项
⚠️ 请确保配置中的 target_groups 群号正确，否则机器人在所有群都会静默

⚠️ 时间格式必须为 HH:MM（如 09:00），错误格式会导致判断失败

⚠️ 本插件优先级为 99，会拦截所有其他插件 —— 这是有意设计，请理解

💡 建议先用 /active_status 确认配置生效后再正式部署

📝 更新日志
v1.0.0 (2024-XX-XX)

🎉 首次发布

✅ 支持指定群聊 + 指定时段双重过滤

✅ 支持跨天时段配置

✅ 支持管理员手动开关

✅ 提供状态查询命令

🤝 贡献 & 反馈
🐛 Bug 反馈：Issues

💡 功能建议：欢迎提 PR 或 Issue

⭐ 觉得有用请点个 Star 支持一下！

📄 License
本项目基于 MIT License 开源。

🙏 致谢
AstrBot — 优秀的多平台聊天机器人框架

感谢所有使用并反馈问题的用户

text
但你没有输出纯粹的md文档
我们注意到用户说“但你没有输出纯粹的md文档”。之前用户要求“整理成一份自述文档，可以更改格式，但我要一份纯粹的自述文档”，然后问“md格式”，我回复了包含```markdown代码块的文本。用户认为这不是“纯粹的md文档”，可能希望直接输出markdown源码而不包裹在代码块中。我需要去掉外层的代码标记，直接输出markdown纯文本。

您说得对，之前输出的是被代码块包裹的 Markdown 内容，不是纯粹的 Markdown 文档。以下是去掉外层代码块后的纯 Markdown 文本，可直接保存为 .md 文件：

markdown
# 📅 astrbot_plugin_scheduled_active

一个让 AstrBot 按时上下班的插件 —— 仅在指定群聊的指定时间段内响应消息，其他时间完全静默，管理员可随时手动开关。

---

## ✨ 功能特性

- 🎯 **指定群聊生效**：仅在配置的群号内激活，其他群完全无视
- ⏰ **定时上下班**：设定每日工作时段，支持跨天时段（如 22:00~06:00）
- 🔇 **完全静默模式**：非激活时段，任何消息（@、/命令、关键词唤醒、LLM 触发）都不会响应
- 🛠️ **管理员手动控制**：可随时强制开启 / 关闭 / 恢复自动模式
- 💬 **私聊白名单**：可选配置允许私聊不受时段限制
- 📊 **状态查询**：一键查看当前模式、时段、目标群聊等完整信息

---

## 📦 安装方法

### 方式一：通过插件市场（推荐）

在 AstrBot WebUI 的「插件市场」中搜索 `scheduled_active` 一键安装。

### 方式二：手动安装

```bash
cd AstrBot/data/plugins/
git clone https://github.com/yourname/astrbot_plugin_scheduled_active.git
然后在 WebUI 中重载插件即可。

目录结构
text
astrbot_plugin_scheduled_active/
├── main.py              # 插件主程序
├── metadata.yaml        # 插件元数据
├── _conf_schema.json    # 配置项定义
├── requirements.txt     # 依赖列表（无额外依赖）
└── README.md            # 本文档
⚙️ 配置说明
进入 AstrBot WebUI → 插件管理 → 找到本插件 → 点击「配置」：

配置项	类型	默认值	说明
target_groups	list	[]	目标群聊ID列表（必填），仅这些群内会响应
start_time	string	09:00	每日激活开始时间（24小时制 HH:MM）
end_time	string	22:00	每日激活结束时间（24小时制 HH:MM）
allow_private	bool	false	是否允许私聊响应（不受时段和群聊限制）
admin_ids	list	[]	管理员QQ号列表（兼容老版本，新版自动识别）
配置示例（普通时段）
json
{
    "target_groups": [123456789, 987654321],
    "start_time": "09:00",
    "end_time": "22:00",
    "allow_private": false
}
跨天时段示例（夜间工作）
json
{
    "start_time": "22:00",
    "end_time": "06:00"
}
💡 插件会自动识别跨天时段，无需额外配置。

🎮 管理员命令
以下命令任何时段均可使用（即使在静默期），且仅限管理员触发。

命令	功能描述
/active_on	🟢 强制开启机器人
