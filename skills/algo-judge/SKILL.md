---
name: algo-judge
description: 算法题出题与自动评测 skill，模拟 OJ 系统。触发词：出算法题、给道算法题、练算法、评测代码、对答案、跑一下我的代码
---

# Algo Judge

算法题出题与评测 skill，模拟 OJ 系统。

## 脚本路径

评测脚本位于 skill 根目录下的 `scripts/judge.ps1`（下文用 `$JUDGE` 指代）。
不要假设固定绝对路径；始终根据当前 `SKILL.md` 所在目录自行解析 skill 根目录。

## 参考资料

- `references/judge.md` — 评测流程说明（多语言编译命令、退出码、比对逻辑）
- `scripts/judge.ps1` — **一键评测脚本**（核心工具）

## 目录规范（出题第一步必须创建）

工作目录在当前工作区下的 `algo/题目名称/`，出题前**必须先创建**完整目录结构：

```
题目名称/
├── problem.md     # 题目描述（方便复习）
├── standard.c     # 标准答案代码
├── testdata/      # 测试数据
│   ├── input_01.txt
│   ├── output_01.txt
│   └── ...
└── user/          # 用户代码和评测脚本都在这里
    ├── judge.bat  # 运行 .\judge 即可评测
    └── (用户代码)
```

**创建命令**（PowerShell）：

```powershell
New-Item -ItemType Directory -Force -Path "<workspace>/algo/题目名称/testdata", "<workspace>/algo/题目名称/user"
```

`<workspace>` 替换为当前工作区根目录。

## 触发条件

- 用户说"出算法题"、"给我一道算法题"、"练练算法"等 → 执行出题流程
- 用户提交代码文件说"评测"、"跑一下"、"对答案"等 → 执行评测流程

## 出题流程

1. **创建目录**（PowerShell 命令见上方）
2. **生成 judge.bat**：将以下内容写入 `user/judge.bat`（用户在 `user/` 目录下运行 `.\judge` 即可评测）：

```bat
@echo off
chcp 65001 >nul 2>&1
pwsh -File "<SKILL_BASE_DIR>/scripts/judge.ps1" -ProblemDir "%cd%\.."
pause
```

`<SKILL_BASE_DIR>` 替换为根据当前 `SKILL.md` 路径解析到的 skill 根目录。

3. **询问难度**：如用户未指定，提供 简单/中等/困难 选项，难度影响数据规模与算法复杂度
3. **生成题目**：题目名称、描述、输入输出格式、样例（至少 2 组）、数据范围与约束
4. **写入 `problem.md`**：包含完整题面
5. **写标准答案**：C/C++ 实现，编译确保无错
6. **构造测试数据**：至少 5 组
   - 2 组样例（与题面一致）
   - 2 组边界（最小/最大输入、空集等）
   - 1~3 组随机/大数据（匹配题目难度对应的规模）
8. **生成标准输出并自测**：
   - 将标准答案**复制一份**到 `user/` 目录
   - 运行评测脚本（见下方命令），确认全部 AC
   - 自测通过后**删除** `user/` 下的标准答案副本
   - 如果自测失败，修复标准答案或测试数据后重新自测
9. **输出给用户**：题面 + 样例 + 测试点说明，提示在 `user/` 目录下写代码，然后双击 `judge.bat` 或在终端运行 `judge` 评测

## 评测流程

用户提交代码后，**优先使用一键评测脚本**：

```powershell
# 基本用法（自动发现 user/ 下的代码）
pwsh -File "<SKILL_BASE_DIR>/scripts/judge.ps1" -ProblemDir "<workspace>/algo/题目名称"

# 指定代码文件
pwsh -File "<SKILL_BASE_DIR>/scripts/judge.ps1" -ProblemDir "<workspace>/algo/题目名称" -UserCode "<workspace>/algo/题目名称/user/solution.cpp"

# 自定义超时
pwsh -File "<SKILL_BASE_DIR>/scripts/judge.ps1" -ProblemDir "<workspace>/algo/题目名称" -TimeoutSec 10
```

`<SKILL_BASE_DIR>` 替换为 skill 根目录，`<workspace>` 替换为当前工作区根目录。

脚本自动完成：编译 → 逐组运行（含超时控制）→ 逐行比对 → 输出结果。

**结果状态**：

| 状态 | 含义 | 颜色 |
|------|------|------|
| AC | 答案正确 | 绿 |
| WA | 答案错误（显示首处不同行） | 红 |
| TLE | 运行超时 | 黄 |
| RE | 运行时错误 | 红 |
| CE | 编译错误 | 红 |

如脚本执行失败，可手动按 `references/judge.md` 中的流程逐步操作。

## 支持语言

| 语言 | 后缀 | 编译命令 |
|------|------|----------|
| C | `.c` | `gcc -O2 -lm` |
| C++ | `.cpp` | `g++ -O2 -lm` |
| Python | `.py` | 直接运行 |
| Java | `.java` | `javac` + `java` |
| Go | `.go` | `go build` |
| Rust | `.rs` | `rustc` |
| JavaScript | `.js` | `node` |

## 注意事项

- 标准答案必须先跑通再给用户
- 测试数据的输入格式必须严格匹配题目描述
- 评测完的临时文件脚本会自动清理（`.judge_tmp/`）
- WA 时只显示首处不同行，避免大数据量刷屏
