# 报告撰写

在 `check_coverage.py` 返回 `ready: true` 后，读取 `sessions/<id>/student_profile.json` 并撰写报告。

## 报告目标

撰写探索性职业报告，不是判定书。

措辞规范：
- 用："当前证据支持……""可以优先探索……""仍需要验证……""这不是最终职业判定……"
- 禁用："你一定适合……""你就是某类型……""最适合你的职业是……"——以及任何心理诊断或人格判定

## 如何阅读 profile.json

`student_profile.json` 的顶层结构：

| 字段 | 内容 |
|------|------|
| `basic_info` | 年级、专业、当前困惑 |
| `metadata` | 有效单元数、确认状态、连续部分确认次数 |
| `riasec_scores` | 6 个维度的分数、置信度、证据 ID 列表 |
| `auxiliary_preferences` | 10 个辅助维度的分数、置信度、证据 ID 列表 |
| `evidence_log` | 完整证据条目（含行为描述、维度变化、置信度、评分理由、`needs_verification` 标记） |
| `open_questions` | 当前仍不确定的问题 |
| `contradictions` | 记录到的矛盾点 |

写报告时：
- 先看 `metadata.effective_units` 判断证据量是否充足
- 从 `riasec_scores` 和 `auxiliary_preferences` 中找到高分 + 高置信度维度的交集——这是核心线索
- 在 `evidence_log` 中对照这些维度的 `evidence_id` 找到原始行为和评分理由——这是你的叙事素材
- 分数高但证据 ID 只有一个 → 可能是单一场景的窄信号，标注"需更多验证"
- `needs_verification: true` 的证据 → 在结论中保留不确定性
- 检查 `contradictions` 和 `open_questions`，决定哪些需要写入报告的"不确定"章节

## 报告结构

不要用固定模板。根据学生的证据、困惑和修正历史选择结构。通常覆盖：

- 当前证据最强的线索（引用 `evidence_id`）
- 仍不确定的部分
- 下一步探索建议
- 从现有证据中不要过度推导什么

## 证据引用规则

每条重要结论必须引用 `evidence_id`。

好：> 当前更稳的线索是 E/I 组合——你多次表现出主动推进和按结果调整策略（E001, E005）。
差：> 你很适合产品经理。

## 个性化建议

- 回应学生的实际困惑（来自 `basic_info.current_confusion`）
- 解释证据如何导向该建议
- 具体到可执行
- 不要仅因为维度分高就推荐对应职业路径——解释从行为到偏好的桥梁
- 在证据薄弱或被纠正过的地方保留不确定性

## 保存

- 终报：`sessions/<id>/report.md`
- 草稿：`sessions/<id>/draft_report.md`
