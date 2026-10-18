# dsh-guard-plan-qc — 劳动保护与安全防护用品配置表核对

[English](README.md) · [简体中文](README-zh.md) · [Español](README-es.md) · [Português](README-pt.md) · [हिन्दी](README-hi.md)

[![DSH Market](https://raw.githubusercontent.com/2BingLing/dsh-market/master/assets/readme/badge-listed-en.svg)](https://dsh.market/)

`dsh-guard-plan-qc` 读取一份劳动防护用品配置表——材料声明的配置人数与配置期间，加每种用品一行——核对这份表格自身的齐备与自洽：每行是否填写品名、规格型号与配置数量，配置数量能否解析为大于零的数字，配置数量能否按配置人数与本机构配置的每人基数推算出来，发放日期是否落在配置期间内，有效截止日期是否晚于发放日期，以及配置表是否覆盖本机构要求的用品类别。

## Install

```sh
dsh plugin --profile <name> add dsh-guard-plan-qc
dsh --profile <name> --dump-config | grep 'dsh-guard-plan-qc'
```

## 实际输出长什么样

![Terminal demo of dsh-guard-plan-qc: real output over its GP-002 fixture](https://raw.githubusercontent.com/PerryLink/dsh-guard-plan-qc/main/docs/assets/dsh-guard-plan-qc-hero.png)

![Animated terminal demo of dsh-guard-plan-qc](https://raw.githubusercontent.com/PerryLink/dsh-guard-plan-qc/main/docs/assets/dsh-guard-plan-qc-demo.gif)

本插件对自己 `GP-002` 测试夹具的**真实输出**，不是示意图。规则库不伪造引文，因此每条发现都会同时写明所引条款，以及该条款原文本次未取得。

## 它回答什么问题

| 你会问 | 它怎么答 |
|---|---|
| 某行填了品名，规格型号空着，会被报出吗？ | 会。`GP-001` 要求每行填写 `requiredFields` 里的字段——出厂为 品名、规格型号、配置数量，可按本机构表式替换——缺哪项就连同缺失的栏目名一并报出该行，空串视为未填。它只核对栏目是否填了，不判断所配用品或其规格是否恰当。 |
| 配置数量栏写的是「若干」，这和填「0」是一回事吗？ | 不是。`GP-002` 把两者分开报：解析不了的值（如「若干」）报为不是数字，能解析但不大于零的值则连同该数字本身报出。「2双」「１，２００」「2 件」都能解析，单位可以连写。数字是否真实、数量够不够，它不核对；`checkQuantity` 为 false 时本条不执行。 |
| 配置人数 20 人，`factors` 里绝缘手套每人 2 双，表中该行只配了 30，能查出来吗？ | 配置了 `factors` 就能。`GP-003` 用每人基数乘以配置人数，差额超过 `tolerance` 的匹配行即报出。`factors` 出厂为空，未配置时本条在 `skipped` 里说明原因，不会静默通过；材料未声明配置人数时同样进 `skipped`。基数是你自己查来的数值，不是国家标准数值，本条不判断它是否合理。 |
| 配置期间是 2026-03-01 至 2026-03-31，某行发放日期写 2026-02-20，会报吗？ | 会。`GP-004` 报出该行发放日期早于 `periodFrom`。配置期间取自材料顶层的 `periodFrom` / `periodTo`；两者都缺时本条进 `skipped`，不会假定任何期间；解析不了的日期单独报出，不会静默跳过。 |
| 有效截止日期与发放日期填了同一天，算通过吗？ | 不算。`GP-005` 要求有效截止日期晚于发放日期，不满足即报出该行；只有该行同时写了这两个日期时才执行。这段有效期够不够长——取决于用品类别与作业环境——本条不判断。 |
| 表里写的是「安全帽」，本机构要求清单里写的是「安全头盔」，会报未覆盖吗？ | 会。`GP-006` 按品名与规格型号做字面包含比对，同一用品换个写法就会被报成未覆盖；请把常见写法一并列入清单，或统一台账用词。`requiredCategories` 出厂为空，未配置时本条进 `skipped`。它只核对类别是否出现，不判断该用品是否适用于本工程。 |

## 依据的标准

| 文件 | 文号 | 引用它的规则 |
|---|---|---|
| 《个体防护装备配备规范》 | GB 39800.1—2020（个体防护装备配备规范 第1部分：总则；标准号不带"/T"⇒强制性；2020-12-24 发布、2022-01-01 实施；主管部门应急管理部；条号本次未取得） | GP-001, GP-002, GP-003, GP-004, GP-005, GP-006 |

**边界（中文译文，以英文原文为准）：** 本插件核对一份**劳动防护用品配置表**，范围限于表格可以要求到的内容——每行是否写明用品名称、规格与数量，数量是否为正数，是否与方案中写明的配发人数相符，发放日期是否落在方案期间之内，失效日期是否晚于发放日期，以及表格是否覆盖你要求的类别。它**不**判定某种用品对某种危害因素是否属于正确的防护、其防护等级是否足够，也不判定其是否属于特种劳动防护用品。

> ### ⚠️ 在采信报告中的引文之前，请先读这一节（以英文原文为准）
>
> **本插件规则库中的每一条 `excerpt` 都明确写着：本次未取得条款原文。** 该制度见于 **GB 39800.1《个体防护装备配备规范》**和《劳动防护用品监督管理规定》。针对本插件的核验过程无法从这些文件中取得逐字条款原文，因此规则库没有转述引文，而是把这一缺口写在 `excerpt` 字段本身，并把诚实的理由写进 `note`。因此一切都封顶在 `warn`（源自原则）或 `info`（本地配置），并有测试断言：没有任何一条规则声称拥有一条它并不拥有的引文。**拿到原文后，必须做两件事：把每条 `excerpt` 替换为真实条款，并把 `kind` 提升为 `direct`。**
>
> **能让本插件真正有力的两个数字，正是它拒绝编造的两个数字。** 每人需要多少件用品（`GP-003` 的 `factors`）以及某个岗位必须覆盖哪些产品类别（`GP-006` 的 `requiredCategories`），取决于*你*项目的危害辨识，而不是某个全国性数字。两者出厂皆为**空**，词表未设置的规则会报告自己进了 `skipped`，而不是通过。

## Compatibility

| 项目 | 状态 |
|---|---|
| Harness | 对等版本范围 `>=0.1.2-rc.1 <0.2.0 \|\| >=0.2.0-0 <0.3.0` —— 已实测同时接受 `0.2.0-rc.2` 与 `0.2.1-rc.2`。**已声明 `engines.dsh`**：0.2.1 起由宿主单独裁决，范围为 `>=0.2.1-0 <0.3.0` |
| Node | `^22.19.0 || >=24.0.0` |
| 平台 | 全平台（纯 ESM；无原生代码、无联网、不调用模型） |
| 工具模式 | `native` / `ptc` 均可；批量校验整个目录时建议 `ptc`，schema 成本只付一次 |

## What it does

规则表、字段说明与行为细节见 [README.md](README.md#what-it-does)（英文主版本）。本插件只列出材料与所引条款之间的字面差异，并对无法执行的检查在 `skipped` 中逐项说明。

## Configuration

全部可调参数都在 `src/config.ts` 的 Schemastery schema 中，只改 `cordis.yml` 即可生效，无需改代码；逐条阈值在 `rules/` 下的规则库文件里。

| 键 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `rulesFile` | string | `rules/guard-plan-qc.yaml` | 规则库文件路径，相对插件包根目录 |
| `disabledRules` | string[] | `[]` | 要停用的规则 id 列表；每条都会出现在 `skipped` 中 |
| `onlyRules` | string[] | `[]` | 只执行这些规则 id；留空表示执行全部规则 |
| `skipNotes` | string | `""` | 附加到每条 `skipped` 说明后的备注 |
| `timeoutMs` | number | `120000` | 工具协作式超时预算（毫秒） |

## Material format

支持 JSON 与 YAML。完整字段示例见 [README.md](README.md#material-format)（英文主版本）。字段在读取层是可选的，由检查引擎校验，因此部分导出的材料会产生"缺项"类差异，而不是让程序崩溃。

## Rule sources

规则数据与代码分离，每条规则都带文件名、文号、按原文自身编号体系的条款号、逐字摘录与来源地址。加载期强制：摘录必须是真实引文且不少于八个字符；依据仅为原则性条款（`kind: derived-from-principle`，严重级上限 `warn`）或本机构配置（`kind: institutional-configuration`，上限 `info`）的检查不得标为 `error`。夸大依据的规则库会在加载期失败，而不会产出一份看起来很有底气的报告。

核验中确认的边界与"刻意没有作出的结论"见 [README.md](README.md#rule-sources)（英文主版本）与随包的 `rules/evidence/` 目录。

## Troubleshooting

- **插件装上了但工具不出现**：确认 `main` 指向 `lib/index.mjs` 且 `pnpm run build` 已生成该文件；`main` 写错会让加载器静默跳过该条目。
- **`dsh plugin add` 报版本不兼容**：peer 范围覆盖 `0.1.x` 与 `0.2.x`；若运行时在其之外，可显式豁免：`dsh plugin --profile <name> allow-version <包名@版本> --dsh-version <runtime> --accept-risk`
- **某条规则没有执行**：查看 `skipped` 数组，其中写明了规则 id 与原因。
- **`check` 报 `manifest-peers` 失败**：静态检查器比对的是一份早于 0.2 世代的硬编码 peer 范围；安装期的 peer 校验以运行时为准。这是 `dsh-plugin-dev` 的已知上游问题。
- **时间看起来偏移**：全部计算都是对输入字符串做墙上时钟运算，不做时区换算。

## Development

```sh
pnpm install
pnpm run typecheck
pnpm test
pnpm run build
node ../scripts/sync-shared.mjs dsh-guard-plan-qc
```

第 4 项把 `../_shared` 的共享件同步进 `src/shared/`；每次改动共享件后都要重跑。

## License

[Apache License 2.0](LICENSE) © 2026 dsh-guard-plan-qc contributors.
