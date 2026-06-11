# 访谈流程 (v1.2)

启动或继续职业生涯访谈时参考本文件。具体阈值和配置见 `data/config.json`。

## 基本原则

- 一次只问一个问题
- 用情景题而非直接询问自我认知
- 对话保持自然，这不是测验或人格测试
- 用通用场景（`data/scenario_bank.json`），不为学历/考研/家庭压力/考公等现实议题单独开辟特殊路径
- AI 在证据提取环节自行解读现实议题，无需专门编程处理

## 访谈循环

```
收集基本信息 → 自选场景提问 → 根据回答质量决定下一步
  → 充分：直接评分
  → 模糊：追问场景续写
  → 理想化：追问取舍/成本
  → 再次模糊：最多追问 N 次（见 config.follow_up.max_per_scenario），之后基于已有信息评分
  → 跳过：学生明显疲惫或抗拒时，礼貌换题或缩短访谈
```

每轮有效回答后：

1. 创建 `round_update.json`（结构见 `references/evidence_extraction.md`）
2. 运行 `python scripts/apply_round.py sessions/<id> sessions/<id>/round_update.json`
3. 运行 `python scripts/check_coverage.py sessions/<id>` 了解覆盖状态

**注意**：阶段小结/纠正轮（`question_id` 不以 S/T 开头）不计入 `effective_units`。需要先完成 6 个场景轮次再总结确认。场景答题轮结束后才能拿到 `ready: true`。

根据覆盖状态决定下一步：

| 覆盖状态 | 下一步 |
|---------|--------|
| `ready: true` | 读取 `student_profile.json`，撰写 `report.md` |
| 单元和维度达标但缺确认 | 做阶段小结，请学生明确确认或修正（确认轮放场景轮次之后） |
| 连续部分确认达上限（config.summary） | 提议转为探索性草稿 |
| 维度仍有缺口 | 从检查报告建议中选场景继续提问。如无合适 S 场景，可用 `career-scenario-designer` 构建 T 场景 |
| 学生明显疲劳 | 礼貌询问是否缩短或下次继续 |

## 开场信息收集

仅收集必要信息：年级、专业、当前困惑（可选，自然引出）。

默认推荐从 `config.question_selection.default_opener_id` 开始，低门槛、高维度覆盖的通用场景。

## 回答质量分类

- `sufficient`：包含具体动作、取舍、约束或例子
- `vague`：只有口号或抽象价值观，没有行动细节
- `idealized`：既要又要，不提任何成本或代价
- `contradictory`：与已有证据矛盾
- `clarification`：学生对题目或场景有疑问

## 追问原则

- 从当前回答和场景中自然生成，不用规则表或固定追问库
- 目标：获取行为细节，不是让学生自我贴标签

好追问：> 如果你发了第一条消息后半天没人回，你会发第二条吗？怎么说？

差追问：> 你更像领导型还是协作型？

单场景最多追问次数见 `config.follow_up.max_per_scenario`。仍不充分则基于已有信息评分并标低置信度，继续下一场景。

## 阶段小结

积累足够证据后，做小结：
> 我先做一个小结，不是最终结论。当前证据显示……这个理解整体准确吗？哪里需要修正？

确认状态：

- `none`：尚未展示
- `partial`：模糊认可（"还行""差不多""基本可以"）
- `confirmed`：明确表示准确
- `corrected`：给出纠正，AI 已更新 profile

仅 `confirmed` 和 `corrected` 满足终报条件。对 `partial` 追问一次明确表态。连续部分确认达 `config.summary.max_consecutive_partials` 则提议转为草稿。

## T 场景（临时定制）

当现有 S 场景无法覆盖学生的特定处境时，可加载 `career-scenario-designer` skill 构建 T 场景：

**触发信号**：学生反复提到 S 场景未覆盖的独特约束；现有场景无法触发某维度但学生背景暗示有信号；学生对某 S 场景感到困惑因为距离他生活太远。

**构建原则**：从学生的实际处境约束推导场景，不是从专业标签推导。思考三个问题——这个学生的实际约束是什么？这个约束会产生什么摩擦？换一个同处境的学生也能回答吗？

**流程**：
1. 加载 `career-scenario-designer` skill
2. 按 T 场景流程编写场景对象 → 写临时文件 → `--single` 验证 → 0 errors 即可用
3. 以 T001 起始编号，直接在访谈中使用
4. 收集回答后按正常流程评分、apply_round（T 场景计入 effective_units）

T 场景不入库。验证只需 0 blocking errors，warnings 可由 AI 自行判断。

## 会话文件

会话目录建在当前工作区下（不在 skill 目录内）：

```
<workspace>/sessions/<id>/
  assessment_log.jsonl       # 追加式审计日志
  student_profile.json       # 当前状态
  report.md                   # 最终报告
```

`<id>` 建议用英文/拼音标识，如 `d1cs`、`zhangsan_2026`。

体验式交流不创建文件，除非用户要求保存。
