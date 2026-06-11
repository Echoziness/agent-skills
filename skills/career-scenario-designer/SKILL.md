---
name: career-scenario-designer
description: 为职业生涯规划设计场景题（通用 S 场景 + 定制 T 场景）
---

# 职业生涯场景设计师

## 安装与路径约定

本 skill 最终会安装到 Codex、OpenCode、Claude Code 等 agent 的 `skills` 目录中。不要假设固定绝对路径；始终根据当前 `SKILL.md` 所在目录和实际可见文件自行解析路径。

默认约定：`career-scenario-designer` 与 `career-planning-agent` 同级安装。因此下面命令中的 `../career-planning-agent/data/scenario_bank.json` 是默认题库路径。如果同级路径不存在，先在当前 agent 的 skills 目录或当前工作区中定位 `career-planning-agent/data/scenario_bank.json`，再替换命令里的题库路径。

## 两种路径

本 skill 支持两种场景设计路径，共享同一套设计原则，仅在验证和存储方式上不同：

| | S 场景（standard） | T 场景（temporary） |
|---|---|---|
| 用途 | 通用题库，任何学生可答 | 针对此学生此处境的定制题 |
| 存储 | `scenario_bank.json`，永久入库 | 内存态，不入库，用后即弃 |
| 验证 | `--warnings-as-errors`，零告警 | `--single` 快速检查 + AI 自检清单 |
| ID | S001, S002, ... | T001, T002, ... |
| 迭代 | 设计 → 验证 → 修改 → 复验 | 单次构建即可用 |

下面先讲共享设计原则，再分别讲两条路径的操作流程。

---

## 共享设计原则

### 不可妥协的规则

不要以这些形式为主要提问：

- "你会怎么判断？"
- "你会怎么考虑？"
- "你更喜欢哪一个？"
- "你是什么类型的人？"
- "你更像研究型还是企业型？"

以上形式仅允许作为场景已产出行动证据后的二次反思。

每个场景必须允许多种非分析性回答都成立：主动推进、等待观察、求助确认、做原型、保护边界、遵循流程、优先关系、降低风险、选择低投入、回避等。

### 题目诱导行为排除

只评分学生在题目之外自发提供的细节：

- 题目让学生对比选项 → 对比本身不是强 I 证据
- 题目提到截止时间 → 提截止时间不是强 C 证据
- 题目说组员沉默 → 注意到沉默不是强 S 证据

### C 常规型保卫线

以下**是** C 证据：偏好清晰规则、喜欢可重复流程、追求稳定预期、重视细节准确、倾向可预测执行、将文档/清单视为首选工作方式。

以下**不是** C 证据：逻辑推理、问题拆解、使用框架、理性取舍、表达清晰。这些属于 I、structured_thinking 或一般认知风格。

### 偏误风险排查

| 风险类型 | 说明 |
|---------|------|
| 分析诱导 | 题目推动学生做抽象推理 |
| 社会赞许性 | 某种回答看起来更正确/更上进 |
| 框架泄漏 | 题目暴露了被测量的维度 |
| 经验门槛 | 缺乏经验的学生无法自然回答 |
| 专业知识偏差 | 回答需要领域知识而非偏好判断 |
| 过度情境化 | 太具体，测试的是对该活动的认知 |
| 情境不足 | 太模糊，迫使学生做泛化分析 |

### 场景要素（v1.2 schema）

每个场景 6 个字段：

| 字段 | 性质 | 写什么 |
|------|------|--------|
| `id` | 标识 | S001-S00N 或 T001-T00N |
| `title` | 展示 | 简短标题，供选择列表辨识 |
| `ask` | **给学生看** | 行动优先的情景提问。直接对学生说的话 |
| `know` | **给 AI 备课** | prose，覆盖角色、触发事件、约束、社会动态、时间压力、赌注 |
| `bias` | 偏误控制 | `risk`/`dont`/`only` 三字段 |
| `rubric` | 评分操作 | 数组，每条含 `when`/`add`/`confidence_condition` |

维度覆盖由脚本从 rubric.add 自动提取，设计者不需要手动声明。

好示例：

> 周三晚上 10 点，你刚写完一半实验报告，明天还有课。你刷到一个和未来职业有关的小项目机会，报名截止是本周五。它看起来有成长价值，但需要接下来两周每天挤时间准备，而且不保证有结果。你现在打开电脑，第一步会做什么？今晚你会怎么处理它？

差示例：

> 你会怎么判断是否继续投入这个方向？你会设置什么验证方式？

### 偏误控制声明

每个场景必须包含：

```json
{
  "bias": {
    "risk": "本题涉及职业抉择，可能诱导分析性决策。",
    "dont": "不要仅因为学生对比选项就给 I/C 分数。",
    "only": "学生自发提及信息来源、验证步骤或不确定性检查时，才记录 I。"
  }
}
```

### 验收清单

场景通过当且仅当：
- 场景在真实学生生活中可能发生
- 提示先问行动再问推理
- 学生无需特定经历即可回答
- 场景有足够摩擦揭示取舍
- 多种回答风格都可以成立
- 偏误风险已列出
- 题目诱导行为已从评分中排除
- 评分规则区分证据与合规（`rubric.when` 含"自发"或"只有"）
- 场景支持自然追问（不依赖固定追问列表）

---

## S 场景流程（stable）

设计通用场景并入库：

1. 以 `references/scenario_schema.json` 为结构参考
2. 按共享原则构建完整场景（6 个必填字段 + rubric 子条目）
3. 将场景对象写入临时文件（如 `temp_S008.json`）
4. 运行验证：`python scripts/validate_scenario_bank.py ../career-planning-agent/data/scenario_bank.json --single temp_S008.json --warnings-as-errors`
5. 有告警则修改场景回到步骤 3，直至 zero errors, zero warnings
6. 用 edit 工具将通过的场景追加到 `../career-planning-agent/data/scenario_bank.json` 的 `scenarios` 数组末尾
7. 运行全库验证确认无伤：`python scripts/validate_scenario_bank.py ../career-planning-agent/data/scenario_bank.json --warnings-as-errors`
8. 更新 `../career-planning-agent/data/scenario_bank.json` 中的 `version` 字段

S 场景的评分标准需涵盖多种有效行为路径，评分发生条件必须写清楚"只有学生自发……时才计分"。

---

## T 场景流程（temporary）

在访谈过程中，当现有 S 场景无法覆盖当前学生的特定处境时，生成临时定制场景。

### 何时使用 T 场景

不是每个学生都需要 T 场景。以下信号之一出现时考虑：

- 学生反复提到一个 S 场景未覆盖的独特约束（如"我们学校项目资源很少""我跨专业基础弱"）
- 现有场景无法触发某维度，但学生背景暗示该维度很可能有信号（如艺术类学生对 A 维度的深度场景）
- 学生对某个 S 场景表现出困惑，因为场景和他的生活经验太远

### T 场景设计原则

构建 T 场景时，AI 思考这三个问题（不是查表）：

1. **这个学生的实际约束是什么？**（课程压力？学校资源？人际关系模式？自我效能感？）
2. **这个约束在真实场景中会产生什么摩擦？**（什么选择是有代价的？代价是什么？）
3. **换一个同处境的学生也能回答吗？**（如果只对这个学生有效，那就是经验门槛——不通过）

**不要做的事**：不要因为"他是计科学生"就写涉及代码知识的场景。场景应来自**处境**，而非**专业标签**。一个金融专业的学生如果一直说自己"做东西"的感受，场景可以涉及动手构建——因为证据来自他的表达，不是他的专业。

### 操作流程

1. AI 在内存中按共享原则 + schema 编写完整场景对象
2. 将场景写入临时 JSON 文件
3. 运行验证（不需要 `--warnings-as-errors`，可以不阻塞）：`python scripts/validate_scenario_bank.py ../career-planning-agent/data/scenario_bank.json --single temp_scene.json`
4. AI 自检验收清单（不需要零告警，但 blocking errors 必须清零）
5. 通过后，以 `T001` 起始编号命名，直接在访谈中使用该场景（不写入 bank.json）
6. 收集回答后按正常流程评分、apply_round

### T 场景质量门

T 场景不要求迭代到零告警，但必须通过最小门控：
- 0 errors（blocking）
- bias.risk/dont/only 均非空
- 每个 rubric 条目的 `when` 含"自发"或"只有"

如果验证报告有 warnings，AI 自行判断是否可接受。场景导入人（即 AI）对质量负责。

---

## 脚本参考

```bash
# 验证全库
python scripts/validate_scenario_bank.py ../career-planning-agent/data/scenario_bank.json --warnings-as-errors

# 验证单个场景（S 或 T 通用）
python scripts/validate_scenario_bank.py ../career-planning-agent/data/scenario_bank.json --single temp_scene.json

# 单场景 + 告警升级为错误
python scripts/validate_scenario_bank.py ../career-planning-agent/data/scenario_bank.json --single temp_scene.json --warnings-as-errors
```

`../career-planning-agent/data/scenario_bank.json` 是默认题库路径。如果目录结构不同，替换为实际题库文件；`--single` 模式只要求该路径指向一个有效题库文件。

## 版本历史

- v1.2：MVP 分发版；统一 skill 名称为 `career-scenario-designer`；补充 Codex/OpenCode/Claude Code 等 agent skills 安装路径约定；修正 v1.2 schema 字段说明、`rubric.when` 质量门、`confidence_condition` 高置信条件字段和默认题库路径命令；完成全库与单场景验证回归。
