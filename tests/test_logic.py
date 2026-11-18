"""机厅人数纯逻辑的单测。

``logic.py`` 刻意不依赖 NoneBot 运行时，所以这里直接用路径导入，
不需要像普通 nonebot 插件那样先 ``nonebot.init()``。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

LOGIC_DIR = Path(__file__).resolve().parents[1] / "nonebot_plugin_mai_arcade"
if str(LOGIC_DIR) not in sys.path:
    sys.path.insert(0, str(LOGIC_DIR))

import logic  # noqa: E402


# ------------------------------------------------------------------ 等待估算


def test_estimate_wait_matches_legacy_output():
    """对齐旧版输出：1 台机、4 个人 → 约 16 分钟，1~1 轮。"""
    estimate = logic.estimate_wait(4, 1)
    assert estimate.players_per_round == 2
    assert estimate.queue_num == 2
    assert (estimate.avg_minutes, estimate.min_minutes, estimate.max_minutes) == (16, 16, 16)
    assert (estimate.min_rounds, estimate.max_rounds) == (1, 1)
    assert estimate.need_wait is True


def test_estimate_wait_no_wait_when_within_one_round():
    estimate = logic.estimate_wait(2, 1)
    assert estimate.queue_num == 0
    assert estimate.need_wait is False
    assert estimate.avg_minutes == 0


def test_estimate_wait_treats_zero_machines_as_one():
    """机台数缺失/为 0 时按 1 台算，避免除零。"""
    assert logic.estimate_wait(4, 0).players_per_round == 2


def test_tip_escalates_with_queue_length():
    def tip(num):
        return logic.resolve_tip(logic.DEFAULT_TIPS, logic.estimate_wait(num, 1).avg_minutes)

    assert tip(2) == "✅ 无需等待，快去出勤吧！"
    assert tip(4) == "✅ 舞萌启动！"        # 16 分钟
    assert tip(6) == "🕰️ 小排队还能忍"      # 32 分钟
    assert tip(100) == "🪦 建议回家（或者明天再来）"


def test_resolve_tip_uses_custom_rules():
    rules = [logic.TipRule(0, "没人"), logic.TipRule(30, "还行")]
    assert logic.resolve_tip(rules, 0) == "没人"
    assert logic.resolve_tip(rules, 30) == "还行"
    assert logic.resolve_tip(rules, 999) == "还行"  # 无命中时退回最后一条
    assert logic.resolve_tip([], 10, fallback="?") == "?"


# ------------------------------------------------------------------ 状态渲染


def test_render_status_matches_legacy_format():
    """整段文本与线上机器人实际输出逐字对齐。"""
    assert logic.render_status(
        "摩兜欢乐岛（盐城滨海吾悦广场店）", 4, 1, verb="人数已更新为"
    ) == (
        "📍 摩兜欢乐岛（盐城滨海吾悦广场店）  人数已更新为 4\n"
        "🕹️ 机台数量：1 台（每轮 2 人）\n"
        "\n"
        "⌛ 预计等待：约 16 分钟\n"
        "   ↳ 范围：16~16 分钟（1~1 轮）\n"
        "\n"
        "💡 ✅ 舞萌启动！"
    )


def test_render_status_without_wait():
    assert logic.render_status("测试店", 2, 1) == (
        "📍 测试店  人数为 2\n"
        "🕹️ 机台数量：1 台（每轮 2 人）\n"
        "\n"
        "✅ 无需等待，快去出勤吧！"
    )


def test_render_status_accepts_configured_tips():
    text = logic.render_status("测试店", 4, 1, tips=[logic.TipRule(0, "无"), logic.TipRule(99, "自定")])
    assert text.endswith("💡 自定")


def test_render_status_appends_updater_info():
    text = logic.render_status("测试店", 2, 1, updated_by="Alice", updated_at="18:20")
    assert text.endswith("\n（Alice · 18:20）")


# ------------------------------------------------------------------ 操作符


@pytest.mark.parametrize(
    ("op", "num", "current", "expected"),
    [
        ("++", None, 3, (4, 1)),
        ("+", 5, 3, (8, 5)),
        ("--", None, 3, (2, -1)),
        ("-", 2, 3, (1, -2)),
        ("=", 10, 3, (10, 0)),
        ("==", 0, 3, (0, 0)),
    ],
)
def test_apply_operator(op, num, current, expected):
    assert logic.apply_operator(op, num, current) == expected


@pytest.mark.parametrize(
    ("op", "num", "current"),
    [
        ("+", 51, 0),     # 单次加超过 50
        ("-", 51, 60),    # 单次减超过 50
        ("+", 100, 50),   # 结果超过 100
        ("-", 5, 3),      # 结果小于 0
        ("=", 101, 0),    # 重置值越界
    ],
)
def test_apply_operator_rejects_illegal(op, num, current):
    with pytest.raises(ValueError, match="拒绝更新"):
        logic.apply_operator(op, num, current)


# ------------------------------------------------------------------ 解析


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("摩兜++", ("摩兜", "++", None)),
        ("摩兜+5", ("摩兜", "+", 5)),
        ("摩兜=10", ("摩兜", "=", 10)),
        ("摩兜10", ("摩兜", "", 10)),
        ("摩兜", ("摩兜", "", None)),
    ],
)
def test_parse_count_command(text, expected):
    assert logic.parse_count_command(text) == expected


def test_parse_count_command_rejects_unrelated_text():
    assert logic.parse_count_command("今天天气不错，去出勤吧") is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("摩兜几人", "摩兜"),
        ("摩兜几", "摩兜"),
        ("摩兜j", "摩兜"),
        ("摩兜", None),
        ("  摩兜几人  ", "摩兜"),  # 前后空格
    ],
)
def test_strip_query_suffix(text, expected):
    assert logic.strip_query_suffix(text) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://nearcade.cn/shops/12733", (None, "12733")),
        ("https://nearcade.cn/shops/12733/", (None, "12733")),
        ("https://nearcade.cn/shops/bemanicn/12733", ("bemanicn", "12733")),
        ("https://nearcade.phizone.cn/shops/nearcade/12733", ("nearcade", "12733")),
        ("", (None, None)),
        ("https://example.com/nothing", (None, None)),
    ],
)
def test_extract_shop_ref(url, expected):
    assert logic.extract_shop_ref(url) == expected


def test_extract_shop_id_is_backwards_compatible():
    assert logic.extract_shop_id("https://nearcade.cn/shops/bemanicn/12733") == "12733"


def test_match_arcade_by_name_and_alias():
    arcades = {"摩兜": {"alias_list": ["md"]}, "其他": {}}
    assert logic.match_arcade(arcades, "摩兜") == "摩兜"
    assert logic.match_arcade(arcades, "md") == "摩兜"
    assert logic.match_arcade(arcades, "不存在") is None


# ------------------------------------------------------------------ 机台选择


def test_pick_maimai_game_prefers_maimai_not_first_entry():
    """真实数据：有的店第一台是湾岸，不能选 games[0]。"""
    games = [
        {"gameId": 10725002, "name": "湾岸MIDNIGHT", "quantity": 4},
        {"gameId": 10725001, "name": "鼓王", "quantity": 1},
        {"gameId": 10725000, "name": "maimai DX", "quantity": 1},
    ]
    assert logic.pick_maimai_game(games) == (10725000, 1)


def test_pick_maimai_game_keeps_first_when_no_maimai():
    games = [
        {"gameId": 14165000, "name": "鼓王", "quantity": 1},
        {"gameId": 14165001, "name": "湾岸MIDNIGHT", "quantity": 4},
    ]
    assert logic.pick_maimai_game(games) == (14165000, 0)


def test_pick_maimai_game_handles_empty_and_dirty_data():
    assert logic.pick_maimai_game([]) == (None, 0)
    assert logic.pick_maimai_game([{"name": "maimai DX"}]) == (None, 1)


# ------------------------------------------------------------------ 上报回复


class _FakeError(Exception):
    """等价于 services.NearcadeError 的最小替身。"""

    def __init__(self, message, status=None, body=""):
        self.status = status
        self.body = body
        super().__init__(message)


def test_render_upload_reply_success():
    assert logic.render_upload_reply("状态文本") == "感谢使用，机厅人数已上传 Nearcade\n状态文本"


def test_render_upload_reply_closed_shop():
    error = _FakeError("Nearcade 返回 HTTP 400", status=400, body='{"message":"closed"}')
    assert logic.render_upload_reply("状态文本", error) == "似乎在Nearcade上这家店关门了😴\n状态文本"


def test_render_upload_reply_local_error_has_no_body_line():
    """未配置 Token 属于本地就能判定的错误，不该出现空的「返回信息」行。"""
    error = _FakeError("尚未配置 Nearcade API Token，请到 https://nearcade.cn/settings/api-tokens 生成后填入")
    text = logic.render_upload_reply("状态文本", error)
    assert text.startswith("尚未配置 Nearcade API Token")
    assert "返回信息" not in text and "上传失败" not in text
    assert text.endswith("状态文本")


def test_render_upload_reply_http_error_keeps_body():
    error = _FakeError("Nearcade 返回 HTTP 500", status=500, body="boom")
    assert logic.render_upload_reply("状态文本", error) == (
        "上传失败: Nearcade 返回 HTTP 500\n返回信息: boom\n\n状态文本"
    )
