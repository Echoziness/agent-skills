#!/usr/bin/env python3
"""career-planning-agent 共享模块：维度常量、覆盖度计算、JSON 读写。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

# ── 维度常量 ──────────────────────────────────────────────────

RIASEC_KEYS = ["R", "I", "A", "S", "E", "C"]

AUX_KEYS = [
    "stability_preference",
    "autonomy",
    "growth_drive",
    "income_sensitivity",
    "social_impact",
    "collaboration_preference",
    "uncertainty_tolerance",
    "structured_thinking",
    "credential_sensitivity",
    "boundary_management",
]

RIASEC_NAMES: dict[str, str] = {
    "R": "现实型",
    "I": "研究型",
    "A": "艺术型",
    "S": "社会型",
    "E": "企业型",
    "C": "常规型",
}

AUX_NAMES: dict[str, str] = {
    "stability_preference": "稳定偏好",
    "autonomy": "自主偏好",
    "growth_drive": "成长驱动",
    "income_sensitivity": "收入敏感度",
    "social_impact": "社会影响",
    "collaboration_preference": "协作偏好",
    "uncertainty_tolerance": "不确定性耐受",
    "structured_thinking": "结构化思维",
    "credential_sensitivity": "学历/证书敏感度",
    "boundary_management": "边界管理",
}

VALID_ANSWER_QUALITIES = {"sufficient", "vague", "idealized", "contradictory", "clarification"}
VALID_CONFIRMATION = {"none", "partial", "confirmed", "corrected"}

# ── JSON 读写 ─────────────────────────────────────────────────

def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        if default is None:
            raise FileNotFoundError(path)
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ── 配置加载 ──────────────────────────────────────────────────

def load_config() -> dict[str, Any]:
    config_path = Path(__file__).resolve().parents[1] / "data" / "config.json"
    return load_json(config_path)


# ── Profile 工具 ──────────────────────────────────────────────

def _base_profile() -> dict[str, Any]:
    return {
        "basic_info": {},
        "metadata": {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": None,
            "effective_units": 0,
            "summary_confirmation_status": "none",
            "consecutive_partials": 0,
        },
        "riasec_scores": {
            key: {"score": 0, "confidence": 0.0, "evidence_ids": []}
            for key in RIASEC_KEYS
        },
        "auxiliary_preferences": {
            key: {"score": 0, "confidence": 0.0, "evidence_ids": []}
            for key in AUX_KEYS
        },
        "evidence_log": [],
        "contradictions": [],
        "open_questions": [],
    }


def empty_profile() -> dict[str, Any]:
    return _base_profile()


def load_profile(profile_path: Path, allow_empty: bool = True) -> dict[str, Any]:
    """加载并规范 profile。allow_empty=False 时文件缺失会抛异常。"""
    if not profile_path.exists():
        if allow_empty:
            return empty_profile()
        raise FileNotFoundError(profile_path)
    return ensure_profile_shape(load_json(profile_path))


def ensure_profile_shape(profile: dict[str, Any]) -> dict[str, Any]:
    """补全 profile 中可能缺失的字段（用于加载旧版本或部分损坏的数据）。"""
    defaults = _base_profile()
    for key, value in defaults.items():
        if key not in profile:
            profile[key] = value
        elif isinstance(value, dict):
            profile[key] = {**value, **profile[key]}
    return profile


# ── 覆盖度计算（系统内唯一权威实现） ──────────────────────────

def dimension_counts(profile: dict[str, Any]) -> tuple[int, int]:
    """返回 (有证据的RIASEC维度数, 有证据的辅助维度数)"""
    riasec = sum(1 for v in profile.get("riasec_scores", {}).values() if v.get("evidence_ids"))
    aux = sum(1 for v in profile.get("auxiliary_preferences", {}).values() if v.get("evidence_ids"))
    return riasec, aux


def missing_dimensions(profile: dict[str, Any]) -> tuple[list[str], list[str]]:
    """返回 (缺失的RIASEC维度, 缺失的辅助维度)"""
    riasec = profile.get("riasec_scores", {})
    aux = profile.get("auxiliary_preferences", {})
    missing_r = [k for k in RIASEC_KEYS if not riasec.get(k, {}).get("evidence_ids")]
    missing_a = [k for k in AUX_KEYS if not aux.get(k, {}).get("evidence_ids")]
    return missing_r, missing_a


def coverage(
    profile: dict[str, Any],
    min_units: int | None = None,
    min_riasec: int | None = None,
    min_aux: int | None = None,
) -> dict[str, Any]:
    """计算当前覆盖度。阈值从 config.json 读取，也可显式覆盖。"""
    config = load_config()
    cfg = config.get("readiness", {})
    summary_cfg = config.get("summary", {})
    min_units = min_units if min_units is not None else cfg.get("min_effective_units", 6)
    min_riasec = min_riasec if min_riasec is not None else cfg.get("min_riasec_dimensions", 4)
    min_aux = min_aux if min_aux is not None else cfg.get("min_auxiliary_dimensions", 3)

    md = profile.get("metadata", {})
    effective_units = int(md.get("effective_units", 0))
    riasec_covered, aux_covered = dimension_counts(profile)
    confirmation_status = md.get("summary_confirmation_status", "none")
    confirmed = confirmation_status in {"confirmed", "corrected"}
    consecutive_partials = int(md.get("consecutive_partials", 0))
    max_partials = int(summary_cfg.get("max_consecutive_partials", 3))

    missing: list[str] = []
    if effective_units < min_units:
        missing.append(f"还需要 {min_units - effective_units} 个有效回答单元")
    if riasec_covered < min_riasec:
        missing.append(f"还需要覆盖 {min_riasec - riasec_covered} 个 RIASEC 维度")
    if aux_covered < min_aux:
        missing.append(f"还需要覆盖 {min_aux - aux_covered} 个辅助偏好维度")
    if not confirmed and cfg.get("require_confirmed_summary", True):
        missing.append("还需要一次学生明确确认的阶段小结")

    # 就绪判定
    ready = len(missing) == 0

    # 推荐下一步
    if ready:
        action = "prepare_report"
        hint = "覆盖度和学生确认均已达标，可以准备最终报告。"
    elif consecutive_partials >= max_partials:
        action = "offer_draft"
        hint = "连续多次部分确认，证据可能不够充分。建议提供探索性草稿而非最终报告。"
    elif not confirmed and effective_units >= min_units and riasec_covered >= min_riasec and aux_covered >= min_aux:
        action = "ask_summary"
        hint = "有效回答和维度覆盖已基本达标，但还缺学生明确确认。"
    else:
        action = "continue"
        hint = "继续提问以补充缺失维度。"

    return {
        "ready": ready,
        "action": action,
        "effective_units": effective_units,
        "riasec_covered": riasec_covered,
        "aux_covered": aux_covered,
        "confirmation_status": confirmation_status,
        "consecutive_partials": consecutive_partials,
        "missing": missing,
        "hint": hint,
    }


# ── 辅助 ──────────────────────────────────────────────────────

def recompute_confidence(profile: dict[str, Any]) -> None:
    """根据证据日志重新计算每个维度的平均置信度。"""
    evidence_by_id = {
        item.get("evidence_id"): item for item in profile.get("evidence_log", [])
    }
    for bucket_name in ["riasec_scores", "auxiliary_preferences"]:
        for entry in profile.get(bucket_name, {}).values():
            ids = entry.get("evidence_ids", [])
            confidences = [
                float(evidence_by_id[eid].get("confidence", 0.0))
                for eid in ids
                if eid in evidence_by_id
            ]
            entry["confidence"] = round(sum(confidences) / len(confidences), 2) if confidences else 0.0


def append_unique(items: list[Any], value: Any) -> None:
    if value not in items:
        items.append(value)
