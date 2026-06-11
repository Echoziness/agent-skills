# 证据提取 (v1.2)

在有效回答单元之后、撰写 `round_update.json` 之前阅读本文件。

## 边界

AI 模型负责语义判断。脚本仅存储和验证结构，不推断动机、不处理纠正、不重写解读。

## 什么算证据

仅对以下内容评分：

- 具体行动
- 实际取舍
- 显性约束
- 步骤序列
- 与行动绑定的动机陈述
- 对先前解读的纠正

不是每句话都需要打分。一个有效回答单元可以产出多条证据，但每条证据都要有清晰的评分理由。

正分表示有支持性证据。负分仅用于明确排斥或反复不适。维度缺失不给负分。

## RIASEC 维度说明

- `R` 现实型：动手操作、工具、设备、实体系统、实际操作
- `I` 研究型：分析、探索、推理、查证、理解复杂问题
- `A` 艺术型：创意表达、设计、内容、审美、非标准化输出
- `S` 社会型：帮助、解释、教育、支持、关注他人
- `E` 企业型：影响、组织、说服、推动、追求结果
- `C` 常规型：偏好规则、惯例、稳定流程、细节准确、可预测系统

**重要**：不要把结构化思维自动评分为 `C`。当学生用结构化工具处理复杂性但未展现对规则/惯例/重复工作的偏好时，使用 `structured_thinking`（辅助维度），而非 `C`。

## 辅助维度说明

- `stability_preference`：偏好可预测风险、稳定路径、确定性回报
- `autonomy`：偏好自主决策、独立主导权
- `growth_drive`：为学习、反馈、能力成长而行动的意愿
- `income_sensitivity`：对金钱、薪资、成本、回报的明确关注
- `social_impact`：希望帮助他人、改善群体体验、创造公共价值
- `collaboration_preference`：偏好与他人协作、共同推进
- `uncertainty_tolerance`：在信息不完整时愿意行动的程度
- `structured_thinking`：使用框架、拆解、边界条件和记录来处理复杂性（不是 RIASEC 的 C）
- `credential_sensitivity`：对学历、证书、学校层次、平台标签等外部证明的依赖
- `boundary_management`：在协作、帮助、责任分配中设置明确边界的能力

现实议题如学历焦虑可能在任何回答中出现。学生提及时作为证据记录，不主动开辟专门场景去追问。

## round_update.json 结构

```json
{
  "round": 1,
  "question_id": "S001",
  "question_text": "场景提示原文",
  "student_answer": "学生原始回答或实义摘要",
  "answer_quality": "sufficient",
  "follow_up_used": false,
  "summary_confirmation_status": "none",
  "basic_info": {},
  "evidence": [
    {
      "evidence_id": "E001",
      "student_text": "学生原话或紧凑摘要",
      "behavior_observed": ["具体行为描述"],
      "dimension_delta": {
        "RIASEC": {"I": 2},
        "auxiliary": {"structured_thinking": 1}
      },
      "confidence": 0.75,
      "reason": "为什么这条行为支持这些维度",
      "needs_verification": false
    }
  ],
  "open_questions": ["当前仍需验证的问题"],
  "contradictions": [],
  "next_action_hint": "对下一步的简短提示"
}
```

## 不确定项

`open_questions` 应反映当前仍有价值的不确定项，不是无差别历史堆积。普通场景轮只放新增或仍未解决的问题；阶段确认/纠正轮用当前未解决列表替换旧列表。

当 `summary_confirmation_status` 为 `confirmed` 或 `corrected` 时，将 `open_questions` 设为仅当前未解决的问题。如果学生纠正已解决所有问题，使用空列表。

## 纠正处理

学生纠正解读时：

- 不要争论
- 记录纠正
- 通过新证据（如有可用证据）调整当前解读
- 将 `summary_confirmation_status` 设为 `corrected`
- 将 `open_questions` 替换为当前列表

旧日志保持追加不变。当前 profile 反映最新纠正后的理解。
