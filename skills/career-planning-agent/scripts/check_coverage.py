#!/usr/bin/env python3
"""检查当前会话的覆盖状态，给出下一步建议和场景排序。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import (
    coverage,
    load_config,
    load_json,
    load_profile,
    missing_dimensions,
)


def answered_ids(session_dir: Path) -> set[str]:
    log_path = session_dir / "assessment_log.jsonl"
    if not log_path.exists():
        return set()
    ids: set[str] = set()
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("evidence"):
            qid = str(record.get("question_id", ""))
            if len(qid) > 1 and qid[0] in ("S", "T") and qid[1:].isdigit():
                ids.add(qid)
    return ids


def scenario_dims(scenario: dict[str, Any]) -> tuple[set[str], set[str]]:
    """从 rubric.add 自动提取场景的 RIASEC 和辅助维度。"""
    from common import RIASEC_KEYS, AUX_KEYS
    riasec: set[str] = set()
    aux: set[str] = set()
    for r in scenario.get("rubric", []):
        for k, v in r.get("add", {}).items():
            if not v:
                continue
            if k in RIASEC_KEYS:
                riasec.add(k)
            elif k in AUX_KEYS:
                aux.add(k)
    return riasec, aux


def rank_scenarios(
    scenarios: list[dict[str, Any]],
    missing_riasec: list[str],
    missing_aux: list[str],
    answered: set[str],
    cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    """根据缺失维度对场景打分排序。"""
    r_weight = cfg.get("question_selection", {}).get("riasec_match_weight", 4)
    a_weight = cfg.get("question_selection", {}).get("auxiliary_match_weight", 2)
    results: list[dict[str, Any]] = []

    for sc in scenarios:
        sid = sc["id"]
        if sid in answered:
            continue
        riasec, aux = scenario_dims(sc)

        r_matches = [k for k in missing_riasec if k in riasec]
        a_matches = [k for k in missing_aux if k in aux]

        score = len(r_matches) * r_weight + len(a_matches) * a_weight
        results.append({
            "id": sid,
            "title": sc["title"],
            "score": score,
            "riasec_matches": r_matches,
            "auxiliary_matches": a_matches,
            "riasec_dimensions": sorted(riasec),
            "auxiliary_dimensions": sorted(aux),
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def scenario_text(scenario: dict[str, Any]) -> str:
    parts = [
        scenario.get("know", ""),
        scenario.get("ask", ""),
    ]
    return "\n".join(p for p in parts if p)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_dir", type=Path, help="会话目录")
    parser.add_argument(
        "--scenario-bank",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "scenario_bank.json",
        help="场景库路径",
    )
    args = parser.parse_args()

    cfg = load_config()
    profile = load_profile(args.session_dir / "student_profile.json")
    cov = coverage(profile)
    answered = answered_ids(args.session_dir)
    missing_r, missing_a = missing_dimensions(profile)

    result = {
        "coverage": cov,
        "missing_riasec": missing_r,
        "missing_auxiliary": missing_a,
        "answered_scenarios": sorted(answered),
    }

    # 如果场景库存在，提供排序建议
    bank_path = args.scenario_bank
    if bank_path.exists():
        bank = load_json(bank_path)
        scenarios = bank.get("scenarios", [])
        ranked = rank_scenarios(scenarios, missing_r, missing_a, answered, cfg)

        result["suggestions"] = []
        default_opener = cfg.get("question_selection", {}).get("default_opener_id", "S001")

        # 判断是否需要推荐开场题
        if not answered:
            opener = next((s for s in scenarios if s["id"] == default_opener), None)
            if opener:
                result["recommended_opener"] = {
                    "id": opener["id"],
                    "title": opener["title"],
                    "reason": "首题推荐：通用场景，低门槛，可同时覆盖多个基础维度。",
                    "prompt": scenario_text(opener),
                }

        # 推荐前3个候选场景
        top3 = ranked[:3]
        for s in top3:
            sc = next((x for x in scenarios if x["id"] == s["id"]), None)
            result["suggestions"].append({
                "id": s["id"],
                "title": s["title"],
                "score": s["score"],
                "riasec_matches": s["riasec_matches"],
                "auxiliary_matches": s["auxiliary_matches"],
                "riasec_dimensions": s["riasec_dimensions"],
                "auxiliary_dimensions": s["auxiliary_dimensions"],
                "prompt": scenario_text(sc) if sc else "",
            })

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
