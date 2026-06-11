# 评测参考

评测脚本 `scripts/judge.ps1` 的内部逻辑说明。一般无需手动操作，直接调用脚本即可。

## 支持语言与编译命令

| 语言 | 后缀 | 编译命令 |
|------|------|----------|
| C | `.c` | `gcc code.c -o code.exe -O2 -lm` |
| C++ | `.cpp` | `g++ code.cpp -o code.exe -O2 -lm` |
| Python | `.py` | 直接 `python code.py` |
| Java | `.java` | `javac Code.java` → `java Code` |
| Go | `.go` | `go build -o code.exe code.go` |
| Rust | `.rs` | `rustc code.rs -o code.exe` |
| JavaScript | `.js` | 直接 `node code.js` |

## 评测流程

1. 解析参数：题目目录、用户代码、超时时间
2. 自动发现 user/ 目录下的代码文件（未指定时）
3. 编译（需要编译的语言），失败则输出 CE
4. 逐组评测：
   - 用 `System.Diagnostics.Process` 启动用户程序
   - 重定向 stdin → `testdata/input_xx.txt`，stdout → 临时文件
   - `WaitForExit(timeout * 1000)`，超时则 Kill → **TLE**
   - 非零退出码 → **RE**
5. 比对输出：逐行 Trim 后比较
   - 行数不同 → WA，报告行数差异
   - 内容不同 → WA，报告首处不同行的行号、期望值、实际值
   - 全部一致 → **AC**
6. 汇总：X/Y 通过，全过退出码 0，否则退出码 1
7. 清理临时目录 `.judge_tmp/`

## 退出码说明（脚本整体）

| 退出码 | 含义 |
|--------|------|
| 0 | 全部 AC |
| 1 | 存在非 AC 的测试点 / 编译失败 / 参数错误 |

## 输出比对细节

- 每行做 `Trim()` 去除首尾空白，避免行末空格/`\r` 导致误判
- 行尾多余空行不影响判定
- WA 时仅显示**首处不同行**，避免大数据刷屏
