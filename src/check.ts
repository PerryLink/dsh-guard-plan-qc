/**
 * Pure check core: `(input, ruleset, options) => Report`.
 *
 * No plugin context, no I/O, no clock and no model access, so the whole rule set
 * is unit-testable without credentials. Every finding carries the verbatim clause
 * that produced it, and every check that could not run is reported in `skipped`
 * so an empty issue list can never be read as "the configuration is complete".
 *
 * The checks are about the table's **completeness and internal consistency**: does
 * every row name a product with a specification and a quantity, does the quantity
 * reconcile with the headcount the plan states, is the issue date inside the plan
 * period. Whether a product is the right protection for a hazard is an
 * occupational-health judgement and nothing here attempts it.
 */

import { disabledAsSkipped, formatBasis } from './shared/rules.ts'
import { paramStrings, ruleById } from './shared/ruleset.ts'
import { issueId, makeReport } from './shared/report.ts'
import { parseWallClock } from './shared/datetime.ts'
import type { Issue, Locator, Report, Skipped } from './shared/report.ts'
import type { Ruleset } from './shared/rules.ts'
import type { EquipmentRow, GuardInput } from './model.ts'

/** Options that come from the plugin configuration rather than the rule pack. */
export interface CheckOptions {
  plugin: string
  checkedAt: string
  disabledRules: readonly string[]
  onlyRules: readonly string[]
  /** The product categories the deployment requires the plan to cover. */
  requiredCategories?: readonly string[]
  skipNotes?: string
}

interface RuleContext {
  input: GuardInput
  ruleset: Ruleset
  issues: Issue[]
  skipped: Skipped[]
  fired: Set<string>
  skipReasons: Map<string, string>
  options: CheckOptions
  add(ruleId: string, locator: Locator, found: string, expected: string, fix?: string): void
  skip(ruleId: string, reason: string): void
}

function locatorOf(row: EquipmentRow, column?: string): Locator {
  const locator: Locator = { row: row.row }
  if (column !== undefined) locator.column = column
  return locator
}

function makeAdd(context: Omit<RuleContext, 'add' | 'skip'>): RuleContext['add'] {
  return (ruleId, locator, found, expected, fix) => {
    const rule = ruleById(context.ruleset, ruleId)
    const issue: Issue = {
      id: issueId(context.ruleset.plugin, ruleId, locator),
      ruleId,
      severity: rule.severity,
      locator,
      found,
      expected,
      basis: formatBasis(rule.basis, rule.alsoBasis ?? []),
    }
    if (fix !== undefined) issue.fix = fix
    context.issues.push(issue)
    context.fired.add(ruleId)
  }
}

/** GP-001 — each row names the product and its specification and quantity. */
function checkRowCompleteness(context: RuleContext): void {
  const ruleId = 'GP-001'
  const rule = ruleById(context.ruleset, ruleId)
  const required = paramStrings(rule, 'requiredFields', ['品名', '规格型号', '配置数量'])
  for (const row of context.input.rows) {
    const missing = required.filter((field) => {
      const value = row.fields[field]
      return value === undefined || value.trim() === ''
    })
    if (missing.length === 0) continue
    context.add(
      ruleId,
      locatorOf(row),
      `第 ${row.row} 行缺少 ${missing.join('、')}`,
      `防护用品配置表每行应填写 ${required.join('、')}`,
      '补齐栏目；本条只核对是否填写，不判断所配用品是否适用',
    )
  }
}

/** GP-002 — a configured quantity is a positive number. */
function checkQuantity(context: RuleContext): void {
  const ruleId = 'GP-002'
  const rule = ruleById(context.ruleset, ruleId)
  if (rule.params.checkQuantity === false) {
    context.skip(ruleId, '规则库配置为不核对配置数量，本条不执行')
    return
  }
  const withQuantity = context.input.rows.filter((row) => row.quantity !== undefined)
  if (withQuantity.length === 0) {
    context.skip(ruleId, '材料没有可识别的配置数量列，无法核对数量')
    return
  }
  for (const row of withQuantity) {
    if (row.quantityValue === undefined) {
      context.add(
        ruleId,
        locatorOf(row, '配置数量'),
        `第 ${row.row} 行配置数量「${row.quantity}」不是数字`,
        '配置数量应写成数字（可带单位，如「2双」）',
        '改用数字填写，例如 2 或 2双',
      )
      continue
    }
    if (row.quantityValue > 0) continue
    context.add(
      ruleId,
      locatorOf(row, '配置数量'),
      `第 ${row.row} 行配置数量为 ${row.quantityValue}`,
      '配置数量应为大于零的数',
      '核对是否漏填或填错；数量为零的用品不应列入配置表',
    )
  }
}

/** GP-003 — the quantity reconciles with the headcount the plan states. */
function checkQuantityAgainstHeadcount(context: RuleContext): void {
  const ruleId = 'GP-003'
  const rule = ruleById(context.ruleset, ruleId)
  const factors = rule.params.factors
  if (!Array.isArray(factors) || factors.length === 0) {
    context.skip(
      ruleId,
      '规则库未配置 factors：每人的配置基数随用品类别与本机构标准变化，本插件不硬编码',
    )
    return
  }
  if (context.input.headcount === undefined) {
    context.skip(ruleId, '材料未声明配置人数（headcount），无法按人数推算应配数量')
    return
  }
  const headcount = context.input.headcount
  for (const raw of factors) {
    if (typeof raw !== 'object' || raw === null) continue
    const entry = raw as Record<string, unknown>
    if (typeof entry.match !== 'string' || typeof entry.perPerson !== 'number') continue
    const tolerance = typeof entry.tolerance === 'number' ? entry.tolerance : 0
    const matches = context.input.rows.filter((row) => (row.name ?? '').includes(entry.match as string))
    for (const row of matches) {
      if (row.quantityValue === undefined) continue
      const expected = entry.perPerson * headcount
      if (Math.abs(row.quantityValue - expected) <= tolerance) continue
      context.add(
        ruleId,
        locatorOf(row, '配置数量'),
        `第 ${row.row} 行「${row.name}」配置数量 ${row.quantityValue}，按配置人数 ${headcount} 人 × 每人 ${entry.perPerson} 应为 ${expected}`,
        `按本机构配置标准，该用品的配置数量应为人数与基数的乘积`,
        '核对人数或数量；本条的基数与容差均来自本机构配置，不是国家标准数值',
      )
    }
  }
}

/** GP-004 — the issue date sits inside the plan period. */
function checkIssueWithinPeriod(context: RuleContext): void {
  const ruleId = 'GP-004'
  const from = parseWallClock(context.input.periodFrom ?? '')
  const to = parseWallClock(context.input.periodTo ?? '')
  const withDate = context.input.rows.filter((row) => row.issuedAt !== undefined)
  if (withDate.length === 0) {
    context.skip(ruleId, '材料没有可识别的发放日期列，无法核对发放时间')
    return
  }
  if (from === undefined && to === undefined) {
    context.skip(ruleId, '材料未声明配置期间（periodFrom/periodTo），无法核对发放日期是否在期间内')
    return
  }
  for (const row of withDate) {
    const issued = parseWallClock(row.issuedAt ?? '')
    if (issued === undefined) {
      context.add(
        ruleId,
        locatorOf(row, '发放日期'),
        `第 ${row.row} 行发放日期「${row.issuedAt}」无法解析为日期`,
        '日期应写成可解析的形式，如 2026-03-15',
        '按本机构统一的日期写法填写',
      )
      continue
    }
    if (from !== undefined && issued.date < from.date) {
      context.add(
        ruleId,
        locatorOf(row, '发放日期'),
        `第 ${row.row} 行发放日期 ${issued.date} 早于配置期间起始日 ${from.date}`,
        '发放日期应在配置期间内',
        '核对日期填写或配置期间的范围',
      )
      continue
    }
    if (to === undefined || issued.date <= to.date) continue
    context.add(
      ruleId,
      locatorOf(row, '发放日期'),
      `第 ${row.row} 行发放日期 ${issued.date} 晚于配置期间结束日 ${to.date}`,
      '发放日期应在配置期间内',
      '核对日期填写或配置期间的范围',
    )
  }
}

/** GP-005 — a row may state an expiry date, and it must follow the issue date. */
function checkExpiry(context: RuleContext): void {
  const ruleId = 'GP-005'
  const pairs = context.input.rows.filter((row) => row.expiresAt !== undefined)
  if (pairs.length === 0) {
    context.skip(ruleId, '材料没有可识别的有效截止日期列，本条不适用')
    return
  }
  for (const row of pairs) {
    const expires = parseWallClock(row.expiresAt ?? '')
    if (expires === undefined) {
      context.add(
        ruleId,
        locatorOf(row, '有效截止日期'),
        `第 ${row.row} 行有效截止日期「${row.expiresAt}」无法解析为日期`,
        '日期应写成可解析的形式，如 2027-03-15',
        '按本机构统一的日期写法填写',
      )
      continue
    }
    if (row.issuedAt === undefined) continue
    const issued = parseWallClock(row.issuedAt)
    if (issued === undefined) continue
    if (expires.date > issued.date) continue
    context.add(
      ruleId,
      locatorOf(row, '有效截止日期'),
      `第 ${row.row} 行有效截止日期 ${expires.date} 不晚于发放日期 ${issued.date}`,
      '有效截止日期应晚于发放日期',
      '核对两个日期的填写；本条不判断该有效期长短是否恰当',
    )
  }
}

/** GP-006 — the plan covers the product categories the deployment requires. */
function checkCategoryCoverage(context: RuleContext): void {
  const ruleId = 'GP-006'
  const rule = ruleById(context.ruleset, ruleId)
  const required = [...(context.options.requiredCategories ?? []), ...paramStrings(rule, 'requiredCategories', [])]
  if (required.length === 0) {
    context.skip(
      ruleId,
      '规则库与配置均未提供 requiredCategories：应按哪些作业类别配备哪些用品随工程与作业类型变化，本插件不硬编码',
    )
    return
  }
  const names = context.input.rows.map((row) => `${row.name ?? ''}${row.specification ?? ''}`).join('\n')
  const uncovered = required.filter((category) => !names.includes(category))
  if (uncovered.length === 0) return
  context.add(
    ruleId,
    {},
    `配置表未覆盖 ${uncovered.length} 个本机构要求的用品类别：${uncovered.join('、')}`,
    `按本机构配置，配置表应覆盖 ${required.join('、')}`,
    '核对是否漏配；本条只按名称做字面包含比对，不判断该用品是否适用于本工程',
  )
}

const CHECKERS: readonly ((context: RuleContext) => void)[] = [
  checkRowCompleteness,
  checkQuantity,
  checkQuantityAgainstHeadcount,
  checkIssueWithinPeriod,
  checkExpiry,
  checkCategoryCoverage,
]

/**
 * Run the whole rule pack against one configuration table.
 * @param input - normalized table.
 * @param ruleset - validated rule pack.
 * @param options - plugin identity, clock value and rule selection.
 * @returns the report, with `skipped` listing every check that did not run.
 */
export function runCheck(input: GuardInput, ruleset: Ruleset, options: CheckOptions): Report {
  const disabled = new Set([...ruleset.disabled, ...options.disabledRules])
  const only = new Set(options.onlyRules)
  const base = {
    input,
    ruleset,
    issues: [] as Issue[],
    skipped: [] as Skipped[],
    fired: new Set<string>(),
    skipReasons: new Map<string, string>(),
    options,
  }
  const context: RuleContext = {
    ...base,
    add: makeAdd(base),
    skip: (ruleId, reason) => {
      base.skipReasons.set(ruleId, reason)
    },
  }

  for (const checker of CHECKERS) checker(context)

  const withNote = (reason: string): string => (options.skipNotes === undefined ? reason : `${reason}；${options.skipNotes}`)
  const skipped: Skipped[] = disabledAsSkipped(ruleset, [...disabled], withNote('该规则在当前配置中被禁用'))
  const already = new Set(skipped.map((entry) => entry.rule))
  for (const [ruleId, reason] of base.skipReasons) {
    if (already.has(ruleId)) continue
    if (disabled.has(ruleId) || (options.onlyRules.length > 0 && !only.has(ruleId))) continue
    skipped.push({ rule: ruleId, reason: withNote(reason) })
    already.add(ruleId)
  }
  for (const rule of ruleset.rules) {
    if (disabled.has(rule.id) || base.fired.has(rule.id) || already.has(rule.id)) continue
    if (options.onlyRules.length > 0 && !only.has(rule.id)) continue
    skipped.push({ rule: rule.id, reason: withNote('材料满足该检查的前置条件且未发现差异条目') })
  }
  if (options.onlyRules.length > 0) {
    const notSelected = ruleset.rules.filter((rule) => !only.has(rule.id) && !disabled.has(rule.id))
    if (notSelected.length > 0) {
      skipped.push({
        rule: notSelected.map((rule) => rule.id).join(','),
        reason: withNote(`本次调用通过 only 参数把执行范围限制为 ${[...only].join(', ')}，上列规则未执行`),
      })
    }
  }

  return makeReport({
    plugin: options.plugin,
    target: input.target,
    rulesetVersion: ruleset.version,
    checkedAt: options.checkedAt,
    issues: context.issues,
    skipped,
  })
}
