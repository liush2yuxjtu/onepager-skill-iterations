# Onepager · 窄门单页 — 技能与迭代仓库

> **少即是门** · Less is Gate. 结论在前，细节折叠，交互即接口。

本仓库把两样东西放进同一个 git 仓库，让读者一眼看清 **AI agent 技能 `/onepager` 是怎么一步步迭代出来的**：

1. **`onepager/`** — 技能本体（含完整 git 历史，经 `git subtree` 导入，13 次提交记录了法则如何一条条长出来）
2. **`onepager-workspace/`** — 评测迭代工作区（v0 基线快照 + iteration-1/2/3 完整评测证据 + 评分脚本 + `history.json` 迭代跟踪）

Claude Code、Pi、Codex 三端均通过符号链接共用 `~/.agents/skills/onepager` 这一份技能源码；本仓库是该源码 + 迭代证据的完整存档。

---

## TL;DR

- **onepager** 是一个给 AI agent 的「窄门哲学」技能：所有交付物收敛成一个**自包含交互式 HTML**——结论一屏可见、细节按需展开、交互即接口（搜索 / 排序 / 聚焦 / 勾选 / 复制一个都不能少）。
- **迭代主线**：v0 通过率 **63.9%** → v1 **100%**（`onepager-workspace/history.json` 判定 `won`，current_best）。
- 当前规模：**14 条法则 · 17 个评测用例 · 16 条带正反例的规则 · 13 次技能提交**。

## 目录结构

```
onepager-skill-iterations/
├── README.md                        ← 你在这（本文件）
├── LICENSE                          # MIT
├── onepager/                        # 技能本体（git subtree，含 13 次提交历史）
│   ├── SKILL.md                     #   核心：14 条法则 + 工作流 + 检查清单 + 反模式
│   ├── README.md                    #   技能自己的说明
│   ├── rules/                       #   16 条带正反例的规则（ia / interact / compose / changes / trust）
│   ├── evals/                       #   17 个评测用例（evals.json）
│   ├── scripts/                     #   focus-server.cjs（可选 loopback 聚焦服务）
│   └── assets/                      #   hero SVG
└── onepager-workspace/              # 评测迭代工作区
    ├── history.json                 #   v0(63.9%) → v1(100%) 迭代跟踪
    ├── skill-snapshot/              #   v0 基线快照（迭代对照的起点）
    ├── iteration-1/                 #   evals 5-7 · 会话产物主动归集
    │   ├── benchmark.md / .json     #     当轮基准数据
    │   └── eval-{5,6,7}-*/          #     每个评测的 with_skill / without_skill 对照产出
    ├── iteration-2/                 #   evals 8-10 · 隐式 recap / handoff
    ├── iteration-3/                 #   evals 11-15 · SVG 主动绘制
    ├── run_eval.py / run_eval_v2.py #   评测运行脚本
    └── grade_runs.py / grade_iteration2.py  # 评分脚本
```

> 说明：`onepager-workspace/` 里各评测的**原始 agent 会话日志**（`*.jsonl`，单文件可达 100MB+，超出 Git / GitHub 单文件上限）已在 `.gitignore` 排除，不入库；`grading.json`、`benchmark.md`、`outputs/` 等可验证证据全部保留。

---

## 迭代如何改进 onepager（核心）

> 方法：每个 iteration 围绕一组**真实缺陷驱动**的评测用例（evals）跑 `with_skill` vs `without_skill`（或新 vs 旧）对照，通过率、耗时、token 三项量化判定是否值得收编进 SKILL.md。每轮被验证有效的做法，沉淀为一条**法则**。

### v0 · 基线（08-08，诞生）

- **有什么**：结论前置 / 交互即接口 / 单文件自包含——法则 1-6 的雏形。
- **评测**：baseline **expectation pass rate 63.9%**。`skill-snapshot/` 即此版本快照。
- **缺什么**：会话产物不主动归集、SVG 会翻车、凭据场景会卡死、布局会过密——这些都是后续 iteration 用真实翻车点去补的。

### v1 · 当前最优（08-13）

- **有什么**：14 条法则全量（含主动归集、SVG 纪律、HITL 凭据、视觉密度）。
- **评测**：通过率 **100%**，`history.json` 判定 `won`。

### iteration-1 · evals 5-7 · 会话产物主动归集（08-11）

| 改进了什么 | 评测证据 | 效果 |
|---|---|---|
| **法则 7**：主动归集当前会话 sub-artifact，不等用户点名"产物在哪" | eval-5 全产物归集 · eval-6 主视频在正文可见 · eval-7 范围排除旧产物 | 带技能 100% / 不带技能 100%（此轮目标是从"会做"到"稳定做对"） |
| 补充：关键媒体（视频/截图）在正文可见，不只藏 `<details>` | eval-6 | 耗时 119.3s vs 124.6s（**−5.3s**） |

**一句话**：让 recap / handoff 类交付物不再"漏产物、藏媒体、混旧会话"。

### iteration-2 · evals 8-10 · 隐式 recap / handoff（08-11）

| 改进了什么 | 评测证据 | 效果 |
|---|---|---|
| 隐式 rich recap / scoped handoff / 空态诚实展示（法则 5、7 强化） | eval-8/9/10 均用"只给 transcript、不给明示指令"的隐式任务 | 带技能 **100% vs 不带 64%**（**+36pp**） |
| — | — | 耗时 103.1s vs 146.7s（**−43.6s**）· token 10158 vs 13716（**−3558**） |

**一句话**：技能价值最大的一轮——"隐式"才是真实工作方式，带技能既更对又更省。

### iteration-3 · evals 11-15 · SVG 主动绘制（08-12）

| 改进了什么 | 评测证据 | 效果 |
|---|---|---|
| **法则 12**：有形状就手写内联 SVG（数据/界面/流程主动画），禁引 chart.js/d3 | eval-11 双路径流程 · eval-13 生命周期 · eval-14 显式画 SVG · eval-15 截图证据内联 | 新旧均 100%，但新版本质更对（不再"只见外框+标题、内部空白"） |
| **法则 11 + eval-12 血泪**：手写 SVG 纪律——`<g>` 包裹徽标、`<text>` 只放纯文本、坐标手算 | eval-12 专门修"SVG 只渲染出外框+空白" | 耗时 170.3s vs 262.4s（**−92.1s**）· token −9625 |

**一句话**：把"讲界面/数据"从文字表格升级为主动手绘 SVG，又快又对，且守住单文件自包含（无 CDN）。

### 基准数据汇总

| 轮次 | 评测 | 带技能 / 新 | 不带技能 / 旧 | Δ通过率 | Δ耗时 | ΔToken |
|---|---|---|---|---|---|---|
| v0 → v1 | history.json | 1.0 | 0.6389 | **+0.36** | — | — |
| iteration-1 | 5,6,7 | 100% ±0 | 100% ±0 | +0.00 | **−5.3s** | +113 |
| iteration-2 | 8,9,10 | 100% ±0 | 64% ±13 | **+0.36** | **−43.6s** | **−3558** |
| iteration-3 | 11-15 | 100% ±0 | 100% ±0 | +0.00 | **−92.1s** | **−9625** |

（数据源：各 `iteration-*/benchmark.md`，每轮 3 次运行取均值。）

---

## 技能本体如何演化（`onepager/` 的 13 次提交）

`onepager/` 的 git 历史按时间记录了法则如何一条条加进来——法则编号随插入顺延，提交信息里的编号是当时的编号：

| 日期 | 提交 | 沉淀进技能的内容 |
|---|---|---|
| 08-08 | `8ce4b0a` | v0 诞生：结论前置、交互即接口、单文件自包含 |
| 08-09 | `6a7f0a8` | README「少即是门」slogan + hero SVG |
| 08-09 | `768c097` | **组合产物 main + subs** 拆分省 token（eval-3 验证 10/10 vs 1/10） |
| 08-10 | `f79e38a` | **改动预览**：冻结窄门条 + 定位闪烁（eval-4） |
| 08-10 | `d89298e` | `rules/` 规则库 12 文件（5 大类，带正反例） |
| 08-10 | `aa8fec9` | **设计稿 vs WebApp 漂移基准**（语义 Fidelity 4 态 + 对抗验证） |
| 08-10 | `585c55e` | **SVG/图片内联默认** + 子产物交付清单（同步 4 平台） |
| 08-12 | `dc2cedb` | snapshot：`.claude` 精简版 SKILL.md（保留历史） |
| 08-12 | `5232649` | **会话产物主动归集** sub-artifact + eval-5 fixtures |
| 08-12 | `89a235c` | evals 1-4 expectations 补齐（10 evals 齐备，可验证断言） |
| 08-12 | `e16954d` | **SVG = 主动绘制数据** + `compose-svg-proactive` 规则 |
| 08-12 | `4619efa` | SVG 扩为数据+界面**双维主动绘制** + evals 13-15 |
| 08-13 | `ad3015e` | **视觉密度与布局纪律**（对称网格 / 轻量结论条 / 留白）+ eval 16/17 补齐 |

## 当前 14 条法则（`onepager/SKILL.md`）

`ia` 结论·窄网关 ｜ `interact` 交互·行动·凭据 ｜ `compose` 内联·SVG·拆分·密度 ｜ `changes` 改动预览 ｜ `trust` 诚实·漂移

1. 结论前置 · 2. 窄网关不搬运 · 3. 交互是接口不是装饰 · 4. 行动闭环 · 5. 诚实可审计 · 6. 单文件自包含 · 7. 会话产物主动归集 · 8. 组合产物 main+subs · 9. 改动预览=冻结窄门条+定位闪烁 · 10. 设计稿vsWebApp漂移基准 · 11. SVG/图片内联默认 · 12. SVG 主动绘制数据与界面 · 13. HITL 人机凭据窄门 · 14. 视觉密度与布局纪律

## 17 个评测用例（`onepager/evals/evals.json`）

- **诊断与瘦身** `1-3`：Mac 发热诊断 · 臃肿验收报告瘦身 · MySQL 慢查询
- **会话归集** `5-10`：全产物归集 · 主视频可见 · 范围排除旧产物 · Pi transcript recap/handoff/空态
- **改动预览** `4`：500KB SPA 改动预览（冻结窄门条 + 子视图跳转）
- **SVG 主动绘制** `11-15`：双路径 WebApp · SVG 渲染修复 · 专家生命周期 · MCP 流程 · 截图证据内联
- **HITL 凭据** `16-17`：CLI 部署登录凭据 · 登录多凭据（密码/key/验证码/二维码）

---

## 如何复现评测

```bash
cd onepager-workspace
# 跑评测（各迭代的具体 eval 列表见对应 iteration-*/benchmark.md）
python3 run_eval_v2.py
# 评分 / 汇总
python3 grade_runs.py
python3 grade_iteration2.py
```

> 每次跑会产生新的 `*.jsonl` 会话日志，已在 `.gitignore` 排除，不会污染仓库。

## 安装技能

```bash
# Claude Code / agent 环境
cp -r onepager ~/.claude/skills/
# 或 ~/.agents/skills/ · ~/.pi/skills/ · ~/.codex/skills/
```

## License

MIT（见 `LICENSE`）。
