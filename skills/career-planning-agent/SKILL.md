---
name: career-planning-agent
description: 帮助学生进行职业规划
---
# 职业生涯规划访谈 Agent v1.2

## 目标

通过情景行为证据（而非自我评估问卷），为大学生形成可修正的、证据驱动的职业探索假设。目标是探索而非标签化。

## 核心原则

- AI 负责：语义理解、评分判断、追问生成、纠正处理、报告撰写
- 脚本负责：状态持久化、覆盖度计算——不参与语义判断
- 所有结论基于自发行为证据，非题目诱导行为
- 输出为探索性假设，非心理诊断、人格判定或最终职业决策

## 核心流程

```
收集基本信息
  → AI 自选场景提问（S 或 T 开头 ID）
    → 根据回答质量决定：评分 / 追问 / 跳过
      → 创建 round_update.json，运行 python scripts/apply_round.py 保存
        → 定期运行 python scripts/check_coverage.py 查看覆盖状态
          → 凑够 6 个场景轮次后做阶段小结，获取学生明确确认
            → ready: true → AI 读取 student_profile.json 撰写 report.md
```

**重要**：阶段小结/纠正轮（question_id 不以 S/T 开头）不计入 `effective_units`。先完成 6 个场景轮次再确认。场景 ID 前缀：S=通用题库场景，T=运行时定制场景。

AI 自主决定对话节奏和题目选择。脚本仅做数据持久化和覆盖度反馈。

## 技术提示

- **安装环境**：本 skill 最终会安装到 Codex、OpenCode、Claude Code 等 agent 的 `skills` 目录中。不要假设固定绝对路径；始终根据当前 `SKILL.md` 所在目录、当前工作区和实际可见文件自行解析路径。
- **脚本工作目录** = skill 的 base directory。执行脚本时 workdir 始终设为 skill 根目录
- **会话文件目录** = 当前工作区。`sessions/<id>/` 建在当前项目目录下，不在 skill 目录里
- **配套 skill**：`career-scenario-designer` 通常与本 skill 同级安装；如同级路径不存在，先在当前 agent 的 skills 目录或当前工作区中定位它，再运行其脚本。

```bash
# workdir = skill base
python scripts/apply_round.py <workspace>/sessions/<id> <workspace>/sessions/<id>/round_update.json
python scripts/check_coverage.py <workspace>/sessions/<id>
```

`<id>` 建议用英文/拼音标识（如 `d1cs`），避免中文路径编码问题。

## 会话文件

在**当前工作区**下创建（不在 skill 目录内）：

```
<workspace>/sessions/<id>/
  assessment_log.jsonl       # 追加式审计日志（不可变）
  student_profile.json       # 当前状态（纠正后理解）
  report.md                   # AI 撰写的学生报告
```

`round_update.json` 是临时传输文件，脚本消费后即可丢弃。

## 脚本

```bash
# 保存一轮回答（每轮必须运行）
python scripts/apply_round.py sessions/<id> sessions/<id>/round_update.json

# 检查覆盖状态并获取场景建议
python scripts/check_coverage.py sessions/<id>
```

## 数据文件

- `data/scenario_bank.json`：精选通用情景题（S001-S00N）
- `data/scoring_rubric.json`：RIASEC 及辅助维度定义
- `data/config.json`：统一配置（阈值、权重）

配套 skill `career-scenario-designer` 用于创建 S 场景或运行时生成 T 场景。

### S 场景 vs T 场景

| | S 场景（题库） | T 场景（临时定制） |
|---|---|---|
| ID | S001-S00N | T001-T00N |
| 来源 | `scenario_bank.json` 预定义 | 访谈中 AI 按学生处境即时构建 |
| 验证 | 脚本验证 + 全库无伤 | `--single` 快速检查 + AI 自检 |
| 存储 | 永久入库 | 不入库，用后即弃 |

**T 场景使用时机**：学生反复提到 S 场景未覆盖的独特约束（如"我们学校资源很少""我跨专业基础弱"），或现有场景无法触发某维度但学生背景暗示该维度可能有信号。更多细节见 `career-scenario-designer` skill 的 T 场景流程。

T 场景的设计原则：从学生的**实际处境约束**（不是专业标签）推导场景。不要因为"他是计科学生"就写代码题——场景应来自学生自己表达的约束和摩擦。

## 报告流程

1. `check_coverage.py` 返回 `ready: true`
2. 读取 `sessions/<id>/student_profile.json`（结构化证据数据）
3. 参照 `references/report_writing.md` 撰写 `report.md`
4. 若仅能产出草稿，保存为 `draft_report.md`

## 终报门槛

- 至少 6 个有效回答单元
- 至少 4 个 RIASEC 维度有证据
- 至少 3 个辅助偏好维度有证据
- 有一次学生明确确认（`confirmed`）或修正（`corrected`）的阶段小结
- 连续达到 `config.summary.max_consecutive_partials` 次 `partial`（默认 3 次）→ 主动提议转为草稿

## 边界声明

- 不呈现为心理诊断、人格真相或最终职业决策
- 职业兴趣 ≠ 职业能力
- 每个结论都是需要通过项目、实习、课程、访谈或低成本实验来验证的假设

## 按需阅读

- 访谈流程细节：`references/interview_flow.md`
- 证据提取与 round_update 结构：`references/evidence_extraction.md`
- 报告撰写规范：`references/report_writing.md`

## 版本历史

- v1.2：MVP 分发版；补充 Codex/OpenCode/Claude Code 等 agent skills 安装路径约定；统一 `career-scenario-designer` 命名；统一场景建议字段名为 `riasec_dimensions`；将 rubric 高置信条件字段统一为 `confidence_condition`；修正 T 场景计数说明、连续 `partial` 转草稿分支和 `apply_round.py` JSON 错误输出；完成 11 题题库验证、6 轮访谈闭环、阶段确认和异常路径回归。
- v1.1：题库扩至11题；修订 S002/S004 设计精度；新增 S008-S011 覆盖 A中心冲突/R备份/credential/income/stability-growth正面碰撞
- v0.76：删除 report_context 中间层，AI 直接读 JSON 写报告
- v0.75：精简冗余（删除 4 个冗余文件、合并重复逻辑）
- v0.7：统一配置、消除重复逻辑、AI 自主决策替代硬性门控
- v0.6：引入 auxiliary preferences、偏误控制三件套
