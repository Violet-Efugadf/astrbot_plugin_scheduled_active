# astrbot_plugin_scheduled_active

> 一个为 [AstrBot](https://github.com/Soulter/AstrBot) 打造的 **定时启用 / 静默** 插件，支持自动上下线提示、手动覆盖、私聊豁免、多群管理。

[![AstrBot](https://img.shields.io/badge/AstrBot-v4.24%2B-blue)](https://github.com/Soulter/AstrBot)
[![Version](https://img.shields.io/badge/version-1.4.2-green)](https://github.com/Violet-Efugadf/astrbot_plugin_scheduled_active)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

---

## ✨ 功能特性

- 🕘 **定时启用**：在指定时段（如 `09:00 ~ 22:00`）才响应群聊消息，其余时间自动静默
- 🌅 **上下线提示**：状态切换时自动向目标群发送早安/晚安提示语，营造拟人化体验
- 🎯 **多群独立管理**：仅对配置中的目标群生效，其他群不受影响
- 💬 **私聊豁免**：可选择让私聊不受时段限制（方便主人随时调试）
- 🛠️ **手动覆盖**：管理员可一键强制开启/关闭，或恢复自动定时模式
- 🚫 **三层拦截**：消息入口、LLM 调用前、消息发送前三重拦截，确保静默期间真正"装睡"
- 📊 **状态面板**：随时查询当前模式、状态、时段、群组等信息

---

## 📦 安装

### 方式 1：通过 AstrBot 插件市场（推荐）

在 AstrBot 管理面板搜索 `scheduled_active` 安装即可。

### 方式 2：手动安装

```bash
cd /path/to/AstrBot/data/plugins
git clone https://github.com/Violet-Efugadf/astrbot_plugin_scheduled_active.git
```

然后在 AstrBot 管理面板重载插件。

---

## ⚙️ 配置项

在 AstrBot 管理面板的「插件管理 → astrbot_plugin_scheduled_active → 配置」中设置：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `start_time` | string | `09:00` | 激活起始时间（24h 制，HH:MM） |
| `end_time` | string | `22:00` | 激活结束时间（支持跨天，如 `22:00`→`06:00`） |
| `target_groups` | list | `[]` | 生效的群号列表，仅这些群在静默时段会被拦截 |
| `admin_ids` | list | `[]` | 插件管理员 QQ 号列表（除框架管理员外的额外授权） |
| `allow_private` | bool | `false` | 是否允许私聊**不受时段限制**永远响应 |
| `enable_broadcast` | bool | `true` | 是否在状态切换时向目标群广播上下线提示 |
| `online_message` | string | `🌅 早安~ 机器人已上线，有事请随时呼叫~` | 上线提示语 |
| `offline_message` | string | `🌙 晚安~ 机器人要去休息了，明天见~` | 下线提示语 |
| `poll_interval` | int | `60` | 状态轮询间隔（秒），决定上下线提示的精度 |

### 配置示例

```yaml
start_time: "09:00"
end_time: "23:30"
target_groups:
  - 1104242761
  - 473420677
admin_ids:
  - 1587482788
allow_private: true
enable_broadcast: true
online_message: "🌅 早安呀~ 我醒啦，今天也请多关照！"
offline_message: "🌙 困死啦，先睡了，有事明天再说~"
poll_interval: 60
```

---

## 🎮 命令列表

所有命令仅 **管理员** 可用（框架管理员或 `admin_ids` 中的用户）。

| 命令 | 说明 |
|------|------|
| `/active_on` | 强制开启机器人（覆盖定时规则） |
| `/active_off` | 强制关闭机器人（覆盖定时规则） |
| `/active_auto` | 恢复自动定时模式 |
| `/active_status` | 查看当前状态（模式 / 时段 / 群组等） |
| `/active_help` | 显示命令帮助 |

> 💡 手动开启/关闭后会立即触发上下线提示广播；恢复自动模式时若状态发生变化也会触发。

---

## 🧠 工作原理

插件通过 AstrBot 的三个高优先级钩子拦截消息：

1. **`event_message_type`** —— 入口拦截，阻止后续插件处理
2. **`on_llm_request`** —— 清空 prompt，阻止 LLM 调用
3. **`on_decorating_result`** —— 清空回复内容，阻止消息发送

后台同时运行一个轮询任务（默认每 60 秒一次）检测时段变化，触发上下线广播。广播通过 **直接调用 OneBot v11 的 `send_group_msg` API** 实现，绕过封装层确保送达。

### 行为矩阵

| 场景 | 群聊（目标群） | 群聊（非目标群） | 私聊（allow_private=true） | 私聊（allow_private=false） |
|------|:---:|:---:|:---:|:---:|
| 激活时段 | ✅ 响应 | ⚪ 不干预* | ✅ 响应 | ❌ 拦截 |
| 静默时段 | ❌ 拦截 | ⚪ 不干预* | ✅ 响应 | ❌ 拦截 |

> *"不干预"指本插件不处理，由其他插件/框架默认逻辑决定是否响应。

---

## 🐛 常见问题

**Q：上下线提示日志显示成功，但群里收不到？**
A：请确认使用的是 v1.4.1+ 版本。旧版本通过 `context.send_message` 发送可能因 `unified_msg_origin` 格式问题静默失败，新版改为直接调用 OneBot `send_group_msg`，兼容性更好。

**Q：静默期间私聊也不响应？**
A：v1.4.2 已修复。请将 `allow_private` 设为 `true`，私聊将永远响应，不受时段限制。

**Q：跨天时段（如 22:00 ~ 06:00）支持吗？**
A：支持。当 `start_time > end_time` 时自动识别为跨天时段。

**Q：能否对不同群设置不同时段？**
A：当前版本不支持。如有需求欢迎提 Issue。

---

## 📋 适配说明

- **AstrBot 版本**：v4.24.2+ 已测试通过
- **平台支持**：当前广播功能仅适配 `aiocqhttp`（OneBot v11，含 NapCat / Lagrange / go-cqhttp 等）
- **拦截功能**：支持所有平台

---

## 📝 更新日志

### v1.4.2
- 🐛 修复私聊在静默时段被错误拦截的问题
- 📊 状态面板新增"私聊响应"展示项

### v1.4.1
- 🔧 上下线广播改为直接调用 OneBot `send_group_msg` API，解决"日志成功但实际未发送"的问题
- 📝 新增平台探测日志，便于排查环境问题

### v1.4.0
- ✨ 新增上下线自动提示广播功能
- ✨ 新增 `enable_broadcast` / `online_message` / `offline_message` / `poll_interval` 配置项
- 🛠️ 手动命令切换状态时同步触发广播

### v1.3.0 及以前
- 基础定时启用/静默功能
- 三层拦截机制
- 管理员命令系统

---

## 🤝 贡献

欢迎提交 Issue 与 PR！

- 仓库地址：<https://github.com/Violet-Efugadf/astrbot_plugin_scheduled_active>
- Bug 反馈：[Issues](https://github.com/Violet-Efugadf/astrbot_plugin_scheduled_active/issues)

---

## 📄 License

[MIT](LICENSE) © Violet-Efugadf

---

## 🙏 致谢

- [AstrBot](https://github.com/Soulter/AstrBot) —— 强大的多平台聊天机器人框架
- 所有为本插件提供反馈和建议的用户
