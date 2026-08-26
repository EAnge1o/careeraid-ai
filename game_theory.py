# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RegretResult:
    """后悔值计算结果"""
    regrets: dict[str, float]  # 各选项后悔值
    utils: dict[str, float]    # 各选项效用
    best_action: str
    recommendation: str
    weights: dict[str, float]  # 各选项推荐权重（基于后悔值反推）


def regret_matching(
    grade_level: float = 70.0,
    introversion: float = 50.0,
    risk_tolerance: float = 50.0,
    family_support: float = 50.0,
) -> RegretResult:
    """
    Regret Matching 算法：根据学生画像计算多条路径的后悔值。

    参数（0-100）：
    - grade_level: 成绩水平（越高越优）
    - introversion: 内向程度（越高越内向，外向性低）
    - risk_tolerance: 风险承受（越高越愿意冒险）
    - family_support: 家庭支持（经济/资源）

    后悔值定义：未选择该策略时，与该策略最优收益的差值。
    此处用简化效用函数模拟，路径包括：
    - 大厂高薪
    - 高成长小厂/初创
    - 国企稳定
    - 体制内（选调生/公务员等）
    - 保研/考研
    - 自由职业/远程
    - 出国深造/海外工作
    """
    # 效用函数（简化线性组合，值域 0-100）
    # 大厂：高薪+高压力，适合外向、抗压、愿冒险
    u_big = (
        0.3 * (100 - introversion) +      # 外向更适合大厂
        0.35 * risk_tolerance +            # 风险承受
        0.2 * grade_level +                # 成绩
        0.15 * (100 - family_support)      # 不太依赖家庭支撑
    )
    # 国企：稳定+慢晋升，适合求稳
    u_state = (
        0.25 * introversion +              # 内向偏好稳定
        0.3 * (100 - risk_tolerance) +     # 求稳
        0.2 * grade_level +
        0.25 * family_support
    )
    # 保研/考研：成绩+家庭支持
    u_grad = (
        0.5 * grade_level +                # 成绩是核心
        0.2 * (100 - risk_tolerance) +     # 能接受延迟
        0.15 * introversion +              # 能静心科研
        0.15 * family_support              # 家庭可支持深造
    )
    # 高成长小厂/初创：高风险、高成长
    u_startup = (
        0.25 * (100 - introversion) +
        0.45 * risk_tolerance +
        0.2 * grade_level +
        0.1 * (100 - family_support)
    )
    # 体制内（除国企外）：极稳
    u_gov = (
        0.3 * introversion +
        0.35 * (100 - risk_tolerance) +
        0.15 * grade_level +
        0.2 * family_support
    )
    # 自由职业/远程：自驱+技能可变现
    u_free = (
        0.25 * introversion +
        0.25 * risk_tolerance +
        0.3 * grade_level +
        0.2 * (100 - family_support)
    )
    # 出国深造/海外工作：成绩+风险承受+家庭支持
    u_abroad = (
        0.4 * grade_level +
        0.25 * risk_tolerance +
        0.2 * (100 - introversion) +
        0.15 * family_support
    )

    utils = {
        "大厂高薪": max(0, min(100, u_big)),
        "高成长小厂/初创": max(0, min(100, u_startup)),
        "国企稳定": max(0, min(100, u_state)),
        "体制内/公务员": max(0, min(100, u_gov)),
        "保研/考研": max(0, min(100, u_grad)),
        "自由职业/远程": max(0, min(100, u_free)),
        "出国深造/海外工作": max(0, min(100, u_abroad)),
    }
    best = max(utils, key=utils.get)
    best_u = utils[best]

    # 后悔值 = 选择其他策略时，相对于最优策略的效用损失
    regrets = {a: max(0, best_u - u) for a, u in utils.items()}

    # 推荐权重：后悔值越大说明“没选它”越亏，反而应提高其推荐度；这里用效用直接作为权重
    total = sum(utils.values()) or 1
    weights = {a: round(u / total, 3) for a, u in utils.items()}

    rec = _build_recommendation(utils, regrets, best)
    return RegretResult(regrets=regrets, utils=utils, best_action=best, recommendation=rec, weights=weights)


def _build_recommendation(utils: dict[str, float], regrets: dict[str, float], best: str) -> str:
    parts = [f"综合后悔值分析，当前最优路径为「{best}」。"]
    for a, r in regrets.items():
        if r > 0 and a != best:
            parts.append(f"未选「{a}」的后悔值约 {r:.1f}；若你更看重该方向，可适当权衡。")
    return " ".join(parts)


def regret_matching_from_profile(profile: dict[str, Any]) -> RegretResult:
    """
    从学生画像（简历解析 + 性格测评）中抽取参数，调用 regret_matching。

    用于 routes.chat_send 中，将结果注入 Agent 上下文。
    """
    dims = profile.get("dimensions") or {}
    pers = profile.get("personality") or {}
    career_interest = profile.get("career_interest") or {}
    resources = profile.get("resources") or []
    constraints = profile.get("constraints") or {}
    user_prefs = profile.get("user_prefs") or {}

    # 成绩：用专业技能+学习能力或竞争力近似
    grade_level = 0.5 * (float(dims.get("专业技能", 50)) + float(dims.get("学习能力", 50)))
    if grade_level < 30:
        grade_level = float(profile.get("competitiveness_score") or 50)
    # 内向：Big Five E 低则内向高
    e_score = float(pers.get("E") or pers.get("extraversion") or 50)
    introversion = max(0, 100 - e_score)
    # 风险承受：开放性+神经质
    o_score = float(pers.get("O") or pers.get("openness") or 50)
    n_score = float(pers.get("N") or pers.get("neuroticism") or 50)
    risk_tolerance = 0.6 * o_score + 0.4 * max(0, 100 - n_score)
    # 家庭支持
    family_support = float(profile.get("family_support") or profile.get("resource_score") or 50)

    # --- 兴趣 & 资源 & 约束对参数的微调 ---
    # 职业兴趣：偏 AI/算法/研发 → 提升风险承受与成绩权重（更愿意冲高成长路径）
    interested_ai = any(k in career_interest for k in ["AI/算法", "大数据", "Java 开发", "前端开发"])
    if interested_ai:
        risk_tolerance = min(100, risk_tolerance + 10)
        grade_level = min(100, grade_level + 5)

    # 资源：家庭行业资源 → 提升 family_support；实习内推 → 提升 risk_tolerance 与 grade_level
    if any("家庭" in r for r in resources):
        family_support = min(100, family_support + 15)
    if any("内推" in r or "实习" in r for r in resources):
        risk_tolerance = min(100, risk_tolerance + 10)
        grade_level = min(100, grade_level + 5)

    # 约束：经济/稳定偏好
    econ = constraints.get("econ_risk") or ""
    if "稳定" in econ:
        risk_tolerance = max(0, risk_tolerance - 15)
        family_support = min(100, family_support + 10)
    elif "成长" in econ or "低薪" in econ:
        risk_tolerance = min(100, risk_tolerance + 10)

    # 用户即时偏好：更想稳定 / 不想出国
    if user_prefs.get("prefer_stable"):
        risk_tolerance = max(0, risk_tolerance - 10)
    if user_prefs.get("avoid_abroad"):
        # 避免海外：通过降低风险偏好间接减少出国路径效用
        risk_tolerance = max(0, risk_tolerance - 10)

    return regret_matching(
        grade_level=grade_level,
        introversion=introversion,
        risk_tolerance=risk_tolerance,
        family_support=family_support,
    )
