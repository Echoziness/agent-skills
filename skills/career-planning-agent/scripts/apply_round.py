#!/usr/bin/env python3
"""上报一轮有效回答，更新 profile，追加日志，返回覆盖状态。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from common import (
    AUX_KEYS,
    RIASEC_KEYS,
    VALID_ANSWER_QUALITIES,
    VALID_CONFIRMATION,
    append_unique,
    coverage,
    ensure_profile_shape,
    load_json,
    load_profile,
    recompute_confidence,
    write_json,
)

REQUIRED_FIELDS = [
    "round",
    "question_id",
    "question_text",
    "student_answer",
    "answer_quality",
    "evidence",
    "open_questions",
    "contradictions",
    "next_action_hint",
]


def apply_update(profile: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    profile = ensure_profile_shape(profile)

    if update.get("basic_info"):
        profile.setdefault("basic_info", {}).update(update["basic_info"])

    evidence_items = update.get("evidence", [])
    question_id = str(update.get("question_id", ""))
    md = profile.setdefault("metadata", {})

    # 判断是否为场景回答（S/T开头的ID），计入有效单元
    is_scenario = len(question_id) > 1 and question_id[0] in ("S", "T") and question_id[1:].isdigit()
    if evidence_items and is_scenario:
        md["effective_units"] = int(md.get("effective_units", 0)) + 1

    # 证据去重校验
    existing_ids = {
        item.get("evidence_id") for item in profile.get("evidence_log", []) if item.get("evidence_id")
    }
    seen_ids: set[str] = set()
    for evidence in evidence_items:
        eid = evidence.get("evidence_id")
        if not eid:
            raise ValueError("每条证据必须包含 evidence_id")
        if eid in existing_ids:
            raise ValueError(f"重复的 evidence_id（已在 profile 中存在）: {eid}")
        if eid in seen_ids:
            raise ValueError(f"本轮更新内重复的 evidence_id: {eid}")
        seen_ids.add(eid)
        # 校验维度合法性
        for key in evidence.get("dimension_delta", {}).get("RIASEC", {}):
            if key not in RIASEC_KEYS:
                raise ValueError(f"未知 RIASEC 维度: {key}")
        for key in evidence.get("dimension_delta", {}).get("auxiliary", {}):
            if key not in AUX_KEYS:
                raise ValueError(f"未知辅助维度: {key}")

    # 写入证据
    for evidence in evidence_items:
        eid = evidence["evidence_id"]
        profile.setdefault("evidence_log", []).append(evidence)
        deltas = evidence.get("dimension_delta", {})
        for key, delta in deltas.get("RIASEC", {}).items():
            entry = profile["riasec_scores"][key]
            entry["score"] += int(delta)
            append_unique(entry["evidence_ids"], eid)
        for key, delta in deltas.get("auxiliary", {}).items():
            entry = profile["auxiliary_preferences"][key]
            entry["score"] += int(delta)
            append_unique(entry["evidence_ids"], eid)

    # 确认状态处理：只有非 "none" 的值才更新 profile，避免场景答题轮覆盖已有确认
    confirmation_status = update.get("summary_confirmation_status", "none")
    if confirmation_status and confirmation_status != "none":
        if confirmation_status not in VALID_CONFIRMATION:
            raise ValueError(f"无效的 summary_confirmation_status: {confirmation_status}")
        md["summary_confirmation_status"] = confirmation_status

        if confirmation_status == "partial":
            md["consecutive_partials"] = int(md.get("consecutive_partials", 0)) + 1
        else:
            md["consecutive_partials"] = 0

        if confirmation_status in {"confirmed", "corrected"} and "open_questions" in update:
            profile["open_questions"] = list(update.get("open_questions", []))
    else:
        # 非确认轮次（含 "none"），只累积 open_questions，不碰确认状态
        for q in update.get("open_questions", []):
            append_unique(profile.setdefault("open_questions", []), q)

    # 矛盾点追加
    for c in update.get("contradictions", []):
        profile.setdefault("contradictions", []).append(c)

    md["updated_at"] = datetime.now().isoformat(timespec="seconds")
    recompute_confidence(profile)
    return profile


def normalize_update(update: dict[str, Any]) -> dict[str, Any]:
    update.setdefault("follow_up_used", False)
    update.setdefault("summary_confirmation_status", "none")
    update.setdefault("basic_info", {})
    return update


def validate_update(update: dict[str, Any]) -> None:
    for field in REQUIRED_FIELDS:
        if field not in update:
            raise ValueError(f"round update 缺少必填字段: {field}")
    if update["answer_quality"] not in VALID_ANSWER_QUALITIES:
        raise ValueError(f"无效的 answer_quality: {update['answer_quality']}")
    status = update.get("summary_confirmation_status")
    if status is not None and status not in VALID_CONFIRMATION:
        raise ValueError(f"无效的 summary_confirmation_status: {status}")
    if not isinstance(update.get("evidence"), list):
        raise ValueError("evidence 必须是列表")
    for item in update["evidence"]:
        for field in ["evidence_id", "student_text", "behavior_observed", "dimension_delta", "confidence", "reason", "needs_verification"]:
            if field not in item:
                raise ValueError(f"证据条目缺少必填字段: {field}")
        deltas = item.get("dimension_delta", {})
        if "RIASEC" not in deltas or "auxiliary" not in deltas:
            raise ValueError("dimension_delta 必须包含 RIASEC 和 auxiliary")
        conf = item.get("confidence")
        if not isinstance(conf, (int, float)) or not 0 <= float(conf) <= 1:
            raise ValueError(f"无效的 confidence ({item.get('evidence_id')}): {conf}")


def append_log(log_path: Path, update: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {"applied_at": datetime.now().isoformat(timespec="seconds"), **update}
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_dir", type=Path, help="会话目录")
    parser.add_argument("round_update", type=Path, help="round_update.json 路径")
    args = parser.parse_args()

    update = normalize_update(load_json(args.round_update))
    validate_update(update)

    profile_path = args.session_dir / "student_profile.json"
    log_path = args.session_dir / "assessment_log.jsonl"

    profile = load_profile(profile_path)
    profile = apply_update(profile, update)

    args.session_dir.mkdir(parents=True, exist_ok=True)
    write_json(profile_path, profile)
    append_log(log_path, update)

    result = {
        "profile_path": str(profile_path),
        "assessment_log_path": str(log_path),
        "coverage": coverage(profile),
        "next_action_hint": update.get("next_action_hint", ""),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True, indent=2), file=sys.stderr)
        raise SystemExit(1)
