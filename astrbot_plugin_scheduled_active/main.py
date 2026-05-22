import datetime
import re
import asyncio
from astrbot.api.star import Context, Star, register
from astrbot.api.event import AstrMessageEvent, filter, MessageChain
from astrbot.api import logger, AstrBotConfig
from astrbot.api.provider import ProviderRequest


@register(
    "astrbot_plugin_scheduled_active",
    "YourName",
    "定时启用插件（含上下线提示）",
    "1.4.2",
    "https://github.com/yourname/astrbot_plugin_scheduled_active"
)
class ScheduledActivePlugin(Star):
    ADMIN_CMDS = {"active_on", "active_off", "active_auto", "active_status", "active_help"}

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.manual_override = None
        self._last_active_state = self._is_active_now()
        self._poll_task = asyncio.create_task(self._poll_state())
        logger.info(f"[ScheduledActive] 插件已加载 v1.4.2，初始状态={'激活' if self._last_active_state else '静默'}")

    # ============ 工具方法 ============

    def _parse_time(self, time_str: str):
        try:
            h, m = time_str.strip().split(":")
            return datetime.time(int(h), int(m))
        except Exception:
            return None

    def _is_in_time_range(self) -> bool:
        start = self._parse_time(self.config.get("start_time", "09:00"))
        end = self._parse_time(self.config.get("end_time", "22:00"))
        if start is None or end is None:
            return False
        now = datetime.datetime.now().time()
        if start <= end:
            return start <= now <= end
        return now >= start or now <= end

    def _is_active_now(self) -> bool:
        if self.manual_override is True:
            return True
        if self.manual_override is False:
            return False
        return self._is_in_time_range()

    def _is_admin(self, event: AstrMessageEvent) -> bool:
        try:
            if event.is_admin():
                return True
        except Exception:
            pass
        sender_id = str(event.get_sender_id())
        admins = self.config.get("admin_ids", [])
        return sender_id in [str(a) for a in admins]

    def _get_raw_text(self, event: AstrMessageEvent) -> str:
        text = event.message_str or ""
        text = re.sub(r'^@\S+\s*', '', text.strip()).strip()
        return text

    def _parse_cmd(self, text: str) -> str:
        if not text:
            return ""
        first = text.split()[0].strip().lower()
        if first.startswith("/"):
            first = first[1:]
        return first

    def _should_block(self, event: AstrMessageEvent) -> bool:
        group_id = event.get_group_id()

        # 私聊：开了 allow_private 就永远放行（不受时段限制）
        if not group_id:
            if self.config.get("allow_private", False):
                return False
            return True

        # 群聊：必须是目标群
        target_groups = self.config.get("target_groups", [])
        if str(group_id) not in [str(g) for g in target_groups]:
            return True

        # 目标群在静默时段则拦截
        if not self._is_active_now():
            return True

        return False

    def _silence(self, event: AstrMessageEvent):
        try:
            event.clear_result()
        except Exception:
            pass
        try:
            event.should_call_llm(False)
        except Exception:
            pass
        try:
            event.stop_event()
        except Exception:
            pass

    # ============ 上下线提示核心逻辑 ============

    async def _poll_state(self):
        """后台循环：每分钟检查一次状态是否变化"""
        await asyncio.sleep(5)
        while True:
            try:
                current = self._is_active_now()
                if current != self._last_active_state:
                    logger.info(f"[ScheduledActive] 状态切换: {self._last_active_state} -> {current}")
                    await self._broadcast_state_change(current)
                    self._last_active_state = current
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[ScheduledActive] 轮询任务异常: {e}")
            await asyncio.sleep(self.config.get("poll_interval", 60))

    def _get_aiocqhttp_bot(self):
        """获取 aiocqhttp 的 bot 实例"""
        try:
            platforms = self.context.platform_manager.get_insts()
        except Exception as e:
            logger.error(f"[ScheduledActive] 获取平台列表失败: {e}")
            return None

        for p in platforms:
            cls_name = type(p).__name__
            if "aiocqhttp" in cls_name.lower() or "Aiocqhttp" in cls_name:
                for attr in ("bot", "client", "_bot", "_client", "cqhttp"):
                    bot = getattr(p, attr, None)
                    if bot is not None:
                        return bot
                logger.warning(f"[ScheduledActive] 平台 {cls_name} 未找到 bot 属性")
        return None

    async def _broadcast_state_change(self, is_active: bool):
        """向所有目标群广播状态变化"""
        if not self.config.get("enable_broadcast", True):
            return

        msg = (self.config.get("online_message", "🌅 早安~ 机器人已上线，有事请随时呼叫~")
               if is_active else
               self.config.get("offline_message", "🌙 晚安~ 机器人要去休息了，明天见~"))

        target_groups = self.config.get("target_groups", [])
        if not target_groups:
            return

        bot = self._get_aiocqhttp_bot()
        if bot is None:
            logger.error("[ScheduledActive] 未找到 aiocqhttp bot 实例，无法广播")
            return

        for group_id in target_groups:
            try:
                await bot.call_action(
                    "send_group_msg",
                    group_id=int(group_id),
                    message=msg
                )
                logger.info(f"[ScheduledActive] ✅ 已向群 {group_id} 发送{'上线' if is_active else '下线'}提示")
            except Exception as e:
                logger.error(f"[ScheduledActive] ❌ 向群 {group_id} 发送失败: {e}")
            await asyncio.sleep(0.5)

    # ============ 钩子 1：消息入口 ============

    @filter.event_message_type(filter.EventMessageType.ALL, priority=99999)
    async def gatekeeper(self, event: AstrMessageEvent):
        text = self._get_raw_text(event)
        cmd = self._parse_cmd(text)

        if cmd in self.ADMIN_CMDS:
            if not self._is_admin(event):
                self._silence(event)
                return
            await self._handle_admin_cmd(event, cmd)
            self._silence(event)
            return

        if self._should_block(event):
            self._silence(event)
            return

    # ============ 钩子 2：LLM 调用前拦截 ============

    @filter.on_llm_request(priority=99999)
    async def block_llm(self, event: AstrMessageEvent, req: ProviderRequest):
        text = self._get_raw_text(event)
        cmd = self._parse_cmd(text)

        if cmd in self.ADMIN_CMDS:
            self._silence(event)
            req.prompt = ""
            return

        if self._should_block(event):
            req.prompt = ""
            self._silence(event)

    # ============ 钩子 3：发送前拦截 ============

    @filter.on_decorating_result(priority=99999)
    async def block_send(self, event: AstrMessageEvent):
        text = self._get_raw_text(event)
        cmd = self._parse_cmd(text)

        if cmd in self.ADMIN_CMDS and self._is_admin(event):
            return

        if self._should_block(event):
            try:
                event.clear_result()
            except Exception:
                pass
            try:
                event.stop_event()
            except Exception:
                pass

    # ============ 管理员命令处理 ============

    async def _handle_admin_cmd(self, event: AstrMessageEvent, cmd: str):
        if cmd == "active_on":
            old = self._is_active_now()
            self.manual_override = True
            await self._reply(event, "✅ 已手动开启机器人（覆盖定时规则）\n使用 /active_auto 恢复定时模式")
            if not old:
                await self._broadcast_state_change(True)
                self._last_active_state = True

        elif cmd == "active_off":
            old = self._is_active_now()
            self.manual_override = False
            await self._reply(event, "🔇 已手动关闭机器人（覆盖定时规则）\n使用 /active_auto 恢复定时模式")
            if old:
                await self._broadcast_state_change(False)
                self._last_active_state = False

        elif cmd == "active_auto":
            old = self._last_active_state
            self.manual_override = None
            new = self._is_active_now()
            status = "激活" if new else "静默"
            await self._reply(event, f"🔄 已恢复定时模式，当前状态：{status}")
            if old != new:
                await self._broadcast_state_change(new)
                self._last_active_state = new

        elif cmd == "active_status":
            await self._reply(event, self._build_status_text())

        elif cmd == "active_help":
            await self._reply(event, self._build_help_text())

    async def _reply(self, event: AstrMessageEvent, text: str):
        try:
            chain = MessageChain().message(text)
            await event.send(chain)
        except Exception as e:
            logger.error(f"[ScheduledActive] send 失败: {e}")

    def _build_status_text(self) -> str:
        start = self.config.get("start_time", "09:00")
        end = self.config.get("end_time", "22:00")
        groups = self.config.get("target_groups", [])
        now = datetime.datetime.now().strftime("%H:%M:%S")

        if self.manual_override is True:
            mode = "手动开启（强制激活）"
        elif self.manual_override is False:
            mode = "手动关闭（强制静默）"
        else:
            mode = "自动定时模式"

        in_range = "✅" if self._is_in_time_range() else "❌"
        active = "✅ 激活" if self._is_active_now() else "🔇 静默"
        broadcast = "✅ 已开启" if self.config.get("enable_broadcast", True) else "❌ 已关闭"
        priv = "✅ 允许" if self.config.get("allow_private", False) else "❌ 禁止"

        return (
            f"📊 机器人状态\n"
            f"━━━━━━━━━━━━\n"
            f"当前模式：{mode}\n"
            f"当前状态：{active}\n"
            f"当前时间：{now}\n"
            f"激活时段：{start} ~ {end} {in_range}\n"
            f"私聊响应：{priv}（不受时段限制）\n"
            f"上下线提示：{broadcast}\n"
            f"目标群数：{len(groups)}\n"
            f"目标群号：{', '.join(map(str, groups)) if groups else '无'}"
        )

    def _build_help_text(self) -> str:
        return (
            "📖 定时启用插件命令\n"
            "━━━━━━━━━━━━\n"
            "/active_on     强制开启\n"
            "/active_off    强制关闭\n"
            "/active_auto   恢复定时模式\n"
            "/active_status 查看状态\n"
            "/active_help   显示帮助"
        )

    async def terminate(self):
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        logger.info("[ScheduledActive] 插件已卸载")