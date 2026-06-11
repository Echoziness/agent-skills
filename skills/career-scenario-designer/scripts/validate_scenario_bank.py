#!/usr/bin/env python3
"""Validate career scenarios against design-quality rules. v1.2 schema.

Modes:
  bank   — python validate_scenario_bank.py bank.json [--warnings-as-errors]
  single — python validate_scenario_bank.py bank.json --single temp_scene.json [--warnings-as-errors]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# ── 合法维度全集 ──────────────────────────────────────────────
RIASEC_KEYS = {"R", "I", "A", "S", "E", "C"}
AUX_KEYS = {
    "stability_preference", "autonomy", "growth_drive",
    "income_sensitivity", "social_impact", "collaboration_preference",
    "uncertainty_tolerance", "structured_thinking",
    "credential_sensitivity", "boundary_management",
}

# ── 必填字段 ──────────────────────────────────────────────────
REQUIRED_SCENARIO_FIELDS = ["id", "title", "ask", "know", "bias", "rubric"]
REQUIRED_BIAS_FIELDS = ["risk", "dont", "only"]
REQUIRED_RUBRIC_FIELDS = ["when", "add", "confidence_condition"]

# ── 检测模式 ──────────────────────────────────────────────────
ABSTRACT_ASK_PATTERNS = [
    "怎么判断", "怎么考虑", "考虑过程", "更喜欢",
    "你是什么类型", "你属于", "你更像",
]
FRAMEWORK_LEAK_PATTERNS = [
    "RIASEC", "霍兰德", "研究型", "现实型",
    "艺术型", "社会型", "企业型", "常规型",
]
C_GUARDRAIL_TERMS = [
    "规则", "流程", "稳定", "重复", "细节",
    "可控", "格式", "标准", "文档", "清单",
]
ANALYSIS_TERMS = [
    "分析", "判断", "权衡", "拆解", "框架", "收益", "理性",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def text_has_any(text: str, patterns: list[str]) -> bool:
    return any(p in text for p in patterns)


def dims_from_rubric(rubric: list[dict]) -> set[str]:
    """从 rubric 的 add 字段中提取所有维度。"""
    dims: set[str] = set()
    for r in rubric:
        for k in r.get("add", {}):
            if r["add"][k]:  # non-zero
                dims.add(k)
    return dims


def validate_scenario(scenario: dict[str, Any], index: int = 1) -> tuple[list[str], list[str]]:
    sid = scenario.get("id", f"index-{index}")
    errors: list[str] = []
    warnings: list[str] = []

    for field in REQUIRED_SCENARIO_FIELDS:
        if field not in scenario:
            errors.append("{}: 缺少必填字段 '{}'。".format(sid, field))
    if errors:
        return errors, warnings

    # bias 子字段
    bias = scenario.get("bias", {})
    for f in REQUIRED_BIAS_FIELDS:
        if not bias.get(f):
            errors.append("{}: bias.{} 不能为空。".format(sid, f))

    # ask 质量检查
    ask = scenario.get("ask", "")
    know = scenario.get("know", "")
    if len(ask) < 40:
        warnings.append("{}: ask 过短（{}字），需要更具体的行动提问。".format(sid, len(ask)))
    if text_has_any(ask, ABSTRACT_ASK_PATTERNS):
        warnings.append("{}: ask 包含抽象/测试型措辞。".format(sid))
    if text_has_any(ask, FRAMEWORK_LEAK_PATTERNS):
        errors.append("{}: ask 泄露了评估框架术语。".format(sid))
    if len(know) < 80:
        warnings.append("{}: know 过短（{}字），需补充约束、社会动态、赌注等摩擦信息。".format(sid, len(know)))

    # rubric
    rubric = scenario.get("rubric", [])
    if not isinstance(rubric, list) or not rubric:
        errors.append("{}: rubric 必须是非空列表。".format(sid))

    for ridx, r in enumerate(rubric, start=1):
        for f in REQUIRED_RUBRIC_FIELDS:
            if f not in r:
                errors.append("{} rubric[{}]: 缺少 '{}'。".format(sid, ridx, f))
        if any(f not in r for f in REQUIRED_RUBRIC_FIELDS):
            continue

        when = r.get("when", "")
        add = r.get("add", {})
        confidence_condition = r.get("confidence_condition", "")
        if not when:
            errors.append("{} rubric[{}]: when 不能为空。".format(sid, ridx))
        if not add:
            errors.append("{} rubric[{}]: add 不能为空。".format(sid, ridx))
        if not confidence_condition:
            errors.append("{} rubric[{}]: confidence_condition 不能为空。".format(sid, ridx))

        # 维度合法性
        for k in add:
            if k not in RIASEC_KEYS and k not in AUX_KEYS:
                errors.append("{} rubric[{}]: '{}' 不是合法维度。".format(sid, ridx, k))

        # C 保卫线
        c_val = int(add.get("C", 0))
        if c_val >= 2 and not text_has_any(when, C_GUARDRAIL_TERMS):
            warnings.append("{} rubric[{}]: C +{} 可能过度评分，when 缺乏 C 保卫线关键词。".format(sid, ridx, c_val))
        if c_val > 0 and text_has_any(when, ANALYSIS_TERMS) and not text_has_any(when, C_GUARDRAIL_TERMS):
            warnings.append("{} rubric[{}]: C 分数可能混淆了结构化分析与 Conventional 常规型兴趣。".format(sid, ridx))

        # 自发行为要求
        if "自发" not in when and "只有" not in when:
            warnings.append("{} rubric[{}]: when 应包含'自发'或'只有'，明确什么自发行为才计分。".format(sid, ridx))

    return errors, warnings


def crosscheck_scenario(scenario: dict[str, Any]) -> list[str]:
    """交叉校验：rubric 中出现的维度是否在全库维度集合内。"""
    errors: list[str] = []
    sid = scenario["id"]
    rubric = scenario.get("rubric", [])
    for ri, r in enumerate(rubric, 1):
        for k in r.get("add", {}):
            if k not in RIASEC_KEYS and k not in AUX_KEYS:
                errors.append("{} rubric[{}]: '{}' 不在任何已知维度列表中。".format(sid, ri, k))
    return errors


def print_results(total: int, errors: list[str], warnings: list[str], strict: bool) -> int:
    for e in errors:
        print("ERROR: " + e)
    for w in warnings:
        print("WARNING: " + w)
    valid = not errors and not (strict and warnings)
    print(json.dumps(
        {"scenarios_validated": total, "errors": len(errors), "warnings": len(warnings), "valid": valid},
        ensure_ascii=False, indent=2))
    return 0 if valid else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario_bank", type=Path)
    parser.add_argument("--single", type=Path, help="验证单个裸场景 JSON")
    parser.add_argument("--warnings-as-errors", action="store_true")
    args = parser.parse_args()

    if args.single:
        try:
            scenario = load_json(args.single)
        except Exception as exc:
            print("ERROR: 无法读取场景 JSON: " + str(exc), file=sys.stderr)
            return 1
        errors, warnings = validate_scenario(scenario)
        errors.extend(crosscheck_scenario(scenario))
        return print_results(1, errors, warnings, args.warnings_as_errors)

    try:
        bank = load_json(args.scenario_bank)
    except Exception as exc:
        print("ERROR: 无法读取场景库 JSON: " + str(exc), file=sys.stderr)
        return 1

    scenarios = bank.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        print("ERROR: scenario bank 必须包含非空的 'scenarios' 列表。", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    all_warnings: list[str] = []
    for index, scenario in enumerate(scenarios, start=1):
        errors, warnings = validate_scenario(scenario, index)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        all_errors.extend(crosscheck_scenario(scenario))

    return print_results(len(scenarios), all_errors, all_warnings, args.warnings_as_errors)


if __name__ == "__main__":
    raise SystemExit(main())
