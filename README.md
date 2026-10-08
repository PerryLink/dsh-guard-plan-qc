# dsh-guard-plan-qc — Labour protection and safety protective equipment configuration table check

`dsh-guard-plan-qc` reads one 劳动防护用品配置表 — the headcount and period the plan states, plus one row per configured product — and checks that table's own completeness and internal consistency: that every row fills 品名 (product name), 规格型号 (specification) and 配置数量 (quantity), that the quantity parses as a number greater than zero, that it reconciles with the headcount the plan states times the per-person factor you configure, that the 发放日期 (issue date) falls inside the plan period, that the 有效截止日期 (expiry date) is later than the issue date, and that the table covers the product categories you require.

## What it answers

| You ask | What it answers |
|---|---|
| A row names the product but leaves 规格型号 empty. Is that reported? | Yes. `GP-001` requires every row to fill the fields in `requiredFields` — shipped as 品名, 规格型号 and 配置数量, replaceable with your own table's columns — and reports the row together with the fields it is missing; an empty string counts as unfilled. It checks that the columns are filled, not whether the product or its specification is the right one. |
| The 配置数量 cell says 若干. Is that the same as a quantity of zero? | No. `GP-002` reports the two separately: a value it cannot parse (such as 若干) is reported as not being a number, while a value that parses but is not greater than zero is reported with the figure itself. `2双`, `１，２００` and `2 件` all parse, unit attached. The rule does not check whether the figure is true or whether the quantity is enough; with `checkQuantity` set to false it does not run at all. |
| The headcount is 20 and `factors` gives 绝缘手套 2 per person, but the row configures 30. Will that be caught? | Yes, once `factors` is configured. `GP-003` multiplies the per-person factor by the headcount and reports a matching row whose quantity differs by more than its `tolerance`. `factors` ships empty, so as delivered the rule reports itself in `skipped` with that reason instead of passing silently; it also reports itself there when the material declares no headcount. The factor is the figure you looked up, not a national one — the rule does not judge whether it is reasonable. |
| The plan period is 2026-03-01 to 2026-03-31 and a 发放日期 reads 2026-02-20. Is it reported? | Yes. `GP-004` reports that row as earlier than `periodFrom`. The period comes from the material's top-level `periodFrom` / `periodTo`; when both are missing the rule reports itself in `skipped` rather than assuming a period, and a date it cannot parse is reported separately instead of being skipped silently. |
| The 有效截止日期 is the same day as the 发放日期. Does it pass? | No. `GP-005` requires the expiry date to be later than the issue date and reports the row when it is not, and it runs only when the row states both dates. Whether that validity period is long enough — it depends on the product and the job — is not judged. |
| The table lists 安全帽 but my required list says 安全头盔. Will it be reported as uncovered? | Yes. `GP-006` compares by literal containment against 品名 and 规格型号, so a different wording for the same product is reported as uncovered; list the common spellings as well, or unify the table's wording. `requiredCategories` ships empty, so as delivered the rule reports itself in `skipped`. It checks only whether the category appears, not whether the product suits the project. |

## Standards it follows

| Document | Number | Cited by rules |
|---|---|---|
| 《个体防护装备配备规范》 | GB 39800.1—2020（个体防护装备配备规范 第1部分：总则；标准号不带"/T"⇒强制性；2020-12-24 发布、2022-01-01 实施；主管部门应急管理部；条号本次未取得） | GP-001, GP-002, GP-003, GP-004, GP-005, GP-006 |

**Boundary:** this plugin checks one **劳动防护用品配置表** for what a table can be held to — that every row
names a product with a specification and a quantity, that the quantity is a positive number, that it
reconciles with the headcount the plan states, that the issue date falls inside the plan period, that an
expiry date follows the issue date, and that the table covers the categories you require. It does **not**
judge whether a given product is the right protection for a given hazard, whether its protection level
suffices, or whether it counts as special protective equipment.

> ### ⚠️ Read this before trusting a citation in the report
>
> **Every `excerpt` in this plugin's rule pack says, in so many words, that the clause text was not
> obtained.** The regime lives in **GB 39800.1《个体防护装备配备规范》** and 《劳动防护用品监督管理规定》.
> The verification pass for this plugin could not retrieve verbatim clause text from them, so rather than
> paraphrase a quotation the pack states the gap in the `excerpt` field itself and puts the honest
> reasoning in `note`. Everything is therefore capped at `warn` (principle-derived) or `info` (locally
> configured), and a test asserts that no rule claims a quotation it does not have. **When the texts are
> in hand, two things must be done: replace each `excerpt` with the real clause, and raise `kind` to
> `direct`.**
>
> **The two numbers that would make this plugin powerful are the two it refuses to invent.** How many
> items each person needs (`GP-003` `factors`) and which product categories a job must cover (`GP-006`
> `requiredCategories`) depend on the hazard identification for *your* project, not on a national figure.
> Both ship **empty**, and a rule whose list is unset reports itself in `skipped` rather than passing.

## Compatibility

| Surface | Status |
|---|---|
| Harness | Peer range `>=0.1.2-rc.1 <0.2.0 \|\| >=0.2.0-0 <0.3.0` — verified to accept both `0.2.0-rc.2` and `0.2.1-alpha.1`. `engines.dsh` is deliberately not declared: it has no reader and cannot reject a host |
| Node | `^22.19.0 || >=24.0.0` |
| Platforms | All (plain ESM; no native code, no network, no model call) |
| Tool mode | Works in `native`, `ptc` and `both`; for a batch of plans use `ptc` |

## What it does

Registers the `guard_plan_qc` tool. It reads one configuration table — rows keyed by the table's own
column names, plus the plan's headcount and period — and returns a report.

| Rule | Check | Severity | Basis kind |
|---|---|---|---|
| `GP-001` | every row names 品名, 规格型号 and 配置数量 | info | local |
| `GP-002` | the quantity parses to a positive number | warn | principle |
| `GP-003` | the quantity reconciles with headcount × per-person factor (off by default) | info | local |
| `GP-004` | the issue date falls inside the plan period | warn | principle |
| `GP-005` | an expiry date is later than the issue date | warn | principle |
| `GP-006` | the table covers your required categories (off by default) | info | local |

## Install

```sh
dsh plugin --profile <name> add dsh-guard-plan-qc
dsh --profile <name> --dump-config | grep 'dsh-guard-plan-qc'
```

## Configuration

| Key | Type | Default | Description |
|---|---|---|---|
| `rulesFile` | string | `rules/guard-plan-qc.yaml` | Rule-pack path, relative to the package root |
| `disabledRules` | string[] | `[]` | Rule ids to stop running; each appears in `skipped` |
| `onlyRules` | string[] | `[]` | Run only these rule ids; empty runs every rule |
| `skipNotes` | string | `""` | Note appended to every `skipped` reason |
| `timeoutMs` | number | `120000` | Cooperative tool timeout budget |

Rule-level parameters worth knowing:

- `GP-001` `requiredFields` — defaults to `[品名, 规格型号, 配置数量]`; replace it with your form's columns.
- `GP-002` `checkQuantity` — set to `false` to stop checking quantities.
- `GP-003` `factors` — your per-person factors, e.g.
  `[{ match: 绝缘手套, perPerson: 2, tolerance: 0 }]`. `match` is a substring test on 品名.
- `GP-006` `requiredCategories` — the products your project must cover, e.g.
  `[安全帽, 绝缘手套, 安全带]`. It can also be passed per call.

## Material format

The tool accepts JSON or YAML:

```yaml
subject: 某某厂房工程
headcount: 20
periodFrom: 2026-03-01
periodTo: 2026-03-31
rows:
  - { 品名: 安全帽,   规格型号: V 型 黄色, 配置数量: "20", 发放日期: 2026-03-05, 有效截止日期: 2028-03-04 }
  - { 品名: 绝缘手套, 规格型号: 12kV,      配置数量: "40", 发放日期: 2026-03-05 }
```

Quantities are read from strings, so a spreadsheet export works as-is: `2双`, `1,200`, `１２` and `1.5`
all parse. A cell that is not a number (`若干`, blank) is reported as unparseable, which is **different**
from a quantity of zero — the two need different fixes, so they produce different findings.

`GP-004` needs `periodFrom` and/or `periodTo`; with neither, it reports itself in `skipped` rather than
assuming a period. `GP-003` needs `headcount`; without it, it says so.

## Rule sources

Rule data lives in `rules/guard-plan-qc.yaml`. The pack's header states the citation gap in full, and each
rule's `note` repeats the part that matters for that rule. The load-time guard that normally enforces "an
excerpt must be a real quotation of at least eight characters" cannot tell a quotation from a description —
so this pack leans on the header, the per-rule notes and a test that asserts every `excerpt` admits the gap.

## Troubleshooting

- **`GP-003` or `GP-006` report themselves as skipped.** Their lists are empty. `factors` and
  `requiredCategories` come from your hazard identification, and the plugin will not guess them.
- **`GP-003` fires on a quantity I set deliberately.** The factor you configured is not the one in use, or
  the headcount in the material is stale. Raise `tolerance`, or fix the factor.
- **`GP-006` fires on a product that is in the table.** The comparison is a literal substring test against
  品名 and 规格型号, so `安全帽` will not match `安全头盔`. List the spellings you use, or normalise the
  table.
- **`GP-004` reports nothing about dates.** No plan period was declared, or the table carries no issue
  date; either way the rule says so in `skipped`.
- **The plugin installs but the tool never appears.** Check that `main` resolves to `lib/index.mjs` and
  that `pnpm run build` produced it; a wrong `main` makes the loader skip the entry silently.
- **`dsh plugin add` refuses the package as incompatible.** The peer range covers `0.1.x` and `0.2.x`; if
  your runtime sits outside it, grant an explicit exemption:
  `dsh plugin --profile <name> allow-version dsh-guard-plan-qc@0.1.0 --dsh-version <runtime> --accept-risk`
- **`check` reports `manifest-peers` as failed.** The static checker compares against a hard-coded peer
  range that predates the 0.2 line. The runtime enforces peer compatibility at install time, so the
  declared range is the correct one; this is a known upstream issue in `dsh-plugin-dev`.

## Development

```sh
pnpm install
pnpm run typecheck   # tsc --noEmit
pnpm test            # vitest, paired fixtures per rule
pnpm run build       # tsdown -> lib/index.mjs + lib/index.d.mts
node ../scripts/sync-shared.mjs dsh-guard-plan-qc   # refresh src/shared from ../_shared
```

## License

[Apache License 2.0](LICENSE) © 2026 dsh-guard-plan-qc contributors.
