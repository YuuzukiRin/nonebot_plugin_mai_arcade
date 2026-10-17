"""机厅人数的纯逻辑。

这里只放不依赖 NoneBot 运行时的计算与解析函数，方便直接单测；
框架胶水（指令注册、数据落盘、网络请求）分别放在 ``handlers/`` 与 ``services.py``。
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

#: 单轮游玩时长（分钟），用于估算等待时间
PER_ROUND_MINUTES = 16
#: 每台机每轮的玩家数
PLAYERS_PER_MACHINE = 2
#: 人数上下限，超出直接拒绝
MIN_COUNT, MAX_COUNT = 0, 100
#: 单次加减的上限，防止误触刷出离谱数值
MAX_DELTA = 50

REJECT_MSG = "检测到非法数值，拒绝更新"

#: Nearcade 上舞萌 DX 的游戏名，用于在机厅游戏列表里定位正确的机台
MAIMAI_GAME_NAME = "maimai DX"

_NAME_PATTERN = re.compile(r"^([\u4e00-\u9fa5\w]+?)([+\-=]{0,2})(\d*)$")
_SHOP_ID_PATTERN = re.compile(r"/(\d+)/?$")
_QUERY_SUFFIXES = ("几人", "几", "j")


@dataclass(frozen=True)
class TipRule:
    """一条等待时间提示规则：``avg_minutes <= max_minutes`` 时命中。"""

    max_minutes: int
    tip: str


#: 默认提示语，与旧版本硬编码的四档一致
DEFAULT_TIPS: tuple[TipRule, ...] = (
    TipRule(0, "✅ 无需等待，快去出勤吧！"),
    TipRule(20, "✅ 舞萌启动！"),
    TipRule(40, "🕰️ 小排队还能忍"),
    TipRule(90, "💀 DBD，纯折磨，建议换店"),
    TipRule(9999, "🪦 建议回家（或者明天再来）"),
)


@dataclass(frozen=True)
class WaitEstimate:
    """按人数与机台数估算出来的排队情况。"""

    queue_num: int
    players_per_round: int
    avg_minutes: int
    min_minutes: int
    max_minutes: int
    min_rounds: int
    max_rounds: int

    @property
    def need_wait(self) -> bool:
        return self.queue_num > 0


def estimate_wait(num: int, machine_count: int) -> WaitEstimate:
    """估算等待时间；人数不足一轮时无需等待。"""
    players_per_round = max(int(machine_count), 1) * PLAYERS_PER_MACHINE
    queue_num = max(int(num) - players_per_round, 0)
    if queue_num <= 0:
        return WaitEstimate(
            queue_num=0,
            players_per_round=players_per_round,
            avg_minutes=0,
            min_minutes=0,
            max_minutes=0,
            min_rounds=0,
            max_rounds=0,
        )

    rounds = queue_num / players_per_round
    min_rounds = queue_num // players_per_round
    max_rounds = math.ceil(rounds)
    return WaitEstimate(
        queue_num=queue_num,
        players_per_round=players_per_round,
        avg_minutes=round(rounds * PER_ROUND_MINUTES),
        min_minutes=min_rounds * PER_ROUND_MINUTES,
        max_minutes=max_rounds * PER_ROUND_MINUTES,
        min_rounds=min_rounds,
        max_rounds=max_rounds,
    )


def resolve_tip(rules: Sequence[Any], avg_minutes: int, fallback: str = "") -> str:
    """按 ``max_minutes`` 升序取第一条命中的提示语。

    ``rules`` 里每个元素只要有 ``max_minutes`` 与 ``tip`` 两个属性即可
    （插件配置里用的是 pydantic 模型，测试里用的是 :class:`TipRule`）。
    没有规则命中时退回最后一条，空列表则用 ``fallback``。
    """
    chosen = fallback
    if rules:
        chosen = rules[-1].tip
    for rule in rules:
        if avg_minutes <= rule.max_minutes:
            chosen = rule.tip
            break
    return chosen


def render_status(
    name: str,
    num: int,
    machine_count: int,
    *,
    verb: str = "人数为",
    tips: Sequence[Any] | None = None,
    updated_by: str | None = None,
    updated_at: str | None = None,
) -> str:
    """渲染人数状态文本（含等待时间建议）。"""
    rules = DEFAULT_TIPS if tips is None else tips
    estimate = estimate_wait(num, machine_count)
    tip = resolve_tip(rules, estimate.avg_minutes)

    lines = [
        f"📍 {name}  {verb} {num}",
        f"🕹️ 机台数量：{machine_count} 台（每轮 {estimate.players_per_round} 人）",
        "",
    ]
    if estimate.need_wait:
        lines += [
            f"⌛ 预计等待：约 {estimate.avg_minutes} 分钟",
            f"   ↳ 范围：{estimate.min_minutes}~{estimate.max_minutes} 分钟"
            f"（{estimate.min_rounds}~{estimate.max_rounds} 轮）",
            "",
            f"💡 {tip}",
        ]
    else:
        lines.append(tip)

    if updated_at and updated_by:
        lines.append(f"（{updated_by} · {updated_at}）")
    return "\n".join(lines)


def render_upload_reply(msg: str, error: Any = None) -> str:
    """渲染人数上报后的回复。

    ``error`` 为 ``None`` 表示上传成功；``status == 400`` 表示机厅在 Nearcade 上关店；
    ``status`` 为 ``None`` 表示本地就能判定的错误（例如未配置 Token），
    这时直接说明原因，不需要「返回信息」一行。
    """
    if error is None:
        return f"感谢使用，机厅人数已上传 Nearcade\n{msg}"
    status = getattr(error, "status", None)
    if status == 400:
        return f"似乎在Nearcade上这家店关门了😴\n{msg}"
    if status is None:
        return f"{error}\n\n{msg}"
    return f"上传失败: {error}\n返回信息: {getattr(error, 'body', '')}\n\n{msg}"


def apply_operator(op: str, num: int | None, current_num: int) -> tuple[int, int]:
    """按操作符算出 ``(新人数, 增量)``，非法输入抛 :class:`ValueError`。

    增量为 0 表示这是重置操作（直接覆盖），否则是加减操作（记增量）。
    """
    if op in ("++", "+", "--", "-"):
        delta = (num or 1) if op in ("++", "+") else -(num or 1)
        if abs(delta) > MAX_DELTA:
            raise ValueError(REJECT_MSG)
        new_num = current_num + delta
    elif op in ("==", "=") or (op == "" and num is not None):
        delta = 0
        new_num = int(num)  # type: ignore[arg-type]
    else:
        raise ValueError("不支持的操作符")

    if new_num < MIN_COUNT or new_num > MAX_COUNT:
        raise ValueError(REJECT_MSG)
    return new_num, delta


def parse_count_command(text: str) -> tuple[str, str, int | None] | None:
    """解析 ``<机厅名><操作符><数字>``，不匹配返回 ``None``。"""
    match = _NAME_PATTERN.match(text.strip())
    if not match:
        return None
    name, op, num_str = match.groups()
    return name, op, int(num_str) if num_str else None


def strip_query_suffix(text: str) -> str | None:
    """去掉查询后缀（``几人`` / ``几`` / ``j``），没有后缀返回 ``None``。"""
    text = text.strip()
    for suffix in _QUERY_SUFFIXES:
        if text.endswith(suffix):
            return text[: -len(suffix)].strip()
    return None


def extract_shop_ref(url: str) -> tuple[str | None, str | None]:
    """从 Nearcade / BEMANICN 地图链接里取出 ``(来源, shop id)``。

    Nearcade 的 URL 形如 ``https://nearcade.cn/shops/{source}/{id}`` 或
    ``https://nearcade.cn/shops/{id}``。来源（``bemanicn`` / ``nearcade``）
    决定 API 要用哪个前缀，取不到就返回 ``None``。
    """
    match = _SHOP_ID_PATTERN.search(url or "")
    if not match:
        return None, None

    shop_id = match.group(1)
    head = (url or "")[: match.start()].rstrip("/")

    marker = "/shops"
    index = head.find(marker)
    if index == -1:
        return None, shop_id

    source = head[index + len(marker):].strip("/") or None
    if source is not None and (
        "/" in source or not re.fullmatch(r"[A-Za-z][\w-]*", source)
    ):
        source = None
    return source, shop_id


def extract_shop_id(url: str) -> str | None:
    """从地图链接里取出 shop id（兼容旧调用）。"""
    return extract_shop_ref(url)[1]


def match_arcade(arcades: Mapping[str, Any], name: str) -> str | None:
    """按机厅名或别名匹配，返回真实机厅名；匹配不到返回 ``None``。"""
    if name in arcades:
        return name
    for arcade_name, info in arcades.items():
        if name in ((info or {}).get("alias_list") or []):
            return arcade_name
    return None


def pick_maimai_game(games: list[dict[str, Any]]) -> tuple[int | None, int]:
    """从机厅的游戏列表里挑出舞萌 DX，返回 ``(gameId, 机台数)``。

    各机厅登记游戏的顺序并不一致，不能假定第一台就是舞萌（例如有的店第一台是
    「鼓王」），否则人数会被同步到错误的机台上。机厅没有登记舞萌时退回第一台，
    此时机台数按 0 处理（与旧逻辑一致）。
    """
    if not games:
        return None, 0

    maimai = next((g for g in games if g.get("name") == MAIMAI_GAME_NAME), None)
    target = maimai if maimai is not None else games[0]

    try:
        game_id = int(target.get("gameId"))
    except (TypeError, ValueError):
        game_id = None

    quantity = int(maimai.get("quantity", 1)) if maimai is not None else 0
    return game_id, quantity
