import { readFile, readdir } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { loadRuleset } from '../src/shared/ruleset.ts'
import { parseMaterial } from '../src/parse.ts'
import { runCheck } from '../src/check.ts'
import { buildView } from '../src/view.ts'
import { findForbiddenWording } from '../src/shared/wording.ts'
import { addDays, diffDays, parseWallClock } from '../src/shared/datetime.ts'
import { parseYaml } from '../src/shared/yaml.ts'
import { numberOf } from '../src/model.ts'
import { Config as ConfigSchema } from '../src/config.ts'
import { inject, name as pluginName, resolvePackageFile, TOOL_NAME } from '../src/index.ts'
import type { Report } from '../src/shared/report.ts'
import type { CheckOptions } from '../src/check.ts'

const here = dirname(fileURLToPath(import.meta.url))
const packageRoot = resolve(here, '..')
const rulesPath = join(packageRoot, 'rules', 'guard-plan-qc.yaml')
const fixturesRoot = join(here, 'fixtures')
const CHECKED_AT = '2026-10-06T00:00:00.000Z'

interface CaseFile {
  ruleId: string
  configure?: Record<string, Record<string, unknown>>
  pairs: { name: string; material: string; expect: { ruleId: string; count: number } }[]
}

async function loadPack() {
  return loadRuleset(await readFile(rulesPath, 'utf8'))
}

function runOptions(overrides: Partial<CheckOptions> = {}): CheckOptions {
  return { plugin: pluginName, checkedAt: CHECKED_AT, disabledRules: [], onlyRules: [], ...overrides }
}

function withConfiguration(ruleset: Awaited<ReturnType<typeof loadPack>>, configure: CaseFile['configure']) {
  if (configure === undefined) return ruleset
  return {
    ...ruleset,
    rules: ruleset.rules.map((rule) =>
      configure[rule.id] === undefined ? rule : { ...rule, params: { ...rule.params, ...configure[rule.id] } },
    ),
  }
}

async function runFixture(materialText: string, target: string, configure?: CaseFile['configure']): Promise<Report> {
  const ruleset = withConfiguration(await loadPack(), configure)
  return runCheck(parseMaterial(materialText, target), ruleset, runOptions())
}

function issuesOf(report: Report, ruleId: string) {
  return report.issues.filter((issue) => issue.ruleId === ruleId)
}

async function ruleDirectories(): Promise<string[]> {
  const entries = await readdir(fixturesRoot, { withFileTypes: true })
  return entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name).sort()
}

async function readCases(directory: string): Promise<CaseFile> {
  return JSON.parse(await readFile(join(fixturesRoot, directory, 'cases.json'), 'utf8')) as CaseFile
}

const GOOD = {
  subject: '某某厂房工程',
  headcount: 20,
  periodFrom: '2026-03-01',
  periodTo: '2026-03-31',
  rows: [{ 品名: '安全帽', 规格型号: 'V 型', 配置数量: '20', 发放日期: '2026-03-05' }],
}

describe('rule pack', () => {
  it('declares a citable basis for every rule', async () => {
    const ruleset = await loadPack()
    expect(ruleset.plugin).toBe(pluginName)
    expect(ruleset.rules.length).toBeGreaterThanOrEqual(6)
    for (const rule of ruleset.rules) {
      expect(rule.basis.document, `${rule.id} document`).not.toBe('')
      expect(rule.basis.clause, `${rule.id} clause`).not.toBe('')
      expect(rule.basis.excerpt.length, `${rule.id} excerpt`).toBeGreaterThanOrEqual(8)
      expect(rule.basis.source, `${rule.id} source`).toMatch(/^https?:\/\//)
      expect(['direct', 'derived-from-principle', 'institutional-configuration']).toContain(rule.basis.kind)
    }
  })

  it('never lets a principle-derived or locally configured check be an error', async () => {
    const ruleset = await loadPack()
    for (const rule of ruleset.rules) {
      if (rule.basis.kind === 'derived-from-principle') expect(rule.severity, rule.id).not.toBe('error')
      if (rule.basis.kind === 'institutional-configuration') expect(rule.severity, rule.id).toBe('info')
    }
  })

  it('admits in every excerpt that no verbatim clause was obtained', async () => {
    const ruleset = await loadPack()
    for (const rule of ruleset.rules) {
      expect(rule.basis.excerpt, rule.id).toContain('本次未取得')
      expect(rule.basis.number, rule.id).toContain('GB 39800.1')
    }
    const source = await readFile(rulesPath, 'utf8')
    expect(source).toContain('**excerpt 一律不是引文。**')
    expect(source).toContain('取得条文后必须做两件事')
  })

  it('says plainly that it does not judge whether a product suits the job', async () => {
    const source = await readFile(rulesPath, 'utf8')
    expect(source).toContain('**不判断某件用品是否适用于某项作业、防护等级是否足够、')
    expect(source).toContain('是否属于特种劳动防护用品**')
  })

  it('ships the local vocabularies empty', async () => {
    const ruleset = await loadPack()
    expect(ruleset.rules.find((rule) => rule.id === 'GP-003')?.params.factors).toEqual([])
    expect(ruleset.rules.find((rule) => rule.id === 'GP-006')?.params.requiredCategories).toEqual([])
  })

  it('refuses a rule pack that overstates a principle-derived check', () => {
    const overstated = [
      'plugin: probe',
      'version: "0"',
      'rules:',
      '  - id: X-001',
      '    title: probe',
      '    severity: error',
      '    basis:',
      '      document: 《X》',
      '      number: X〔2020〕1号',
      '      clause: 第一条',
      '      excerpt: 这是一个足够长的逐字摘录示例。',
      '      kind: derived-from-principle',
      '      source: https://example.invalid/x',
    ].join('\n')
    expect(() => loadRuleset(overstated)).toThrow(/strongest permitted severity/)
  })
})

describe('paired fixtures', () => {
  it('has both a compliant and a violating sample for every rule', async () => {
    const ruleset = await loadPack()
    const covered = new Set<string>()
    for (const directory of await ruleDirectories()) {
      const cases = await readCases(directory)
      expect(cases.pairs.filter((pair) => pair.expect.count === 0).length, `${directory} compliant sample`).toBeGreaterThanOrEqual(1)
      expect(cases.pairs.filter((pair) => pair.expect.count > 0).length, `${directory} violating sample`).toBeGreaterThanOrEqual(1)
      for (const pair of cases.pairs) {
        const material = await readFile(join(fixturesRoot, directory, pair.material), 'utf8')
        const report = await runFixture(material, pair.material, cases.configure)
        const matched = issuesOf(report, cases.ruleId)
        expect(
          matched.length,
          `${directory}/${pair.name} expected ${pair.expect.count} × ${cases.ruleId}, got ${matched.map((issue) => issue.found).join(' | ')}`,
        ).toBe(pair.expect.count)
        covered.add(cases.ruleId)
      }
    }
    for (const rule of ruleset.rules) expect(covered.has(rule.id), `covered ${rule.id}`).toBe(true)
  })

  it('gives every issue a citable basis and a stable id', async () => {
    for (const directory of await ruleDirectories()) {
      const cases = await readCases(directory)
      for (const pair of cases.pairs) {
        const material = await readFile(join(fixturesRoot, directory, pair.material), 'utf8')
        const report = await runFixture(material, pair.material, cases.configure)
        for (const issue of report.issues) {
          expect(issue.basis).toContain('「')
          expect(issue.id).toMatch(/^dsh-guard-plan-qc\.GP-\d{3}\.[0-9a-f]{8}$/)
          expect(issue.found).not.toBe('')
          expect(issue.expected).not.toBe('')
        }
      }
    }
  })
})

describe('quantity reading', () => {
  it('accepts the shapes a configuration table uses', () => {
    expect(numberOf('20')).toBe(20)
    expect(numberOf('2双')).toBe(2)
    expect(numberOf('1,200')).toBe(1200)
    expect(numberOf('１２')).toBe(12)
    expect(numberOf('1.5')).toBe(1.5)
    expect(numberOf('若干')).toBeUndefined()
    expect(numberOf(undefined)).toBeUndefined()
  })

  it('separates "not a number" from "not positive"', async () => {
    const ruleset = await loadPack()
    const unparsed = runCheck(
      parseMaterial(JSON.stringify({ ...GOOD, rows: [{ 品名: '安全帽', 配置数量: '若干' }] }), 'inline'),
      ruleset,
      runOptions(),
    )
    expect(issuesOf(unparsed, 'GP-002')[0]?.found).toContain('不是数字')
    const zero = runCheck(
      parseMaterial(JSON.stringify({ ...GOOD, rows: [{ 品名: '安全帽', 配置数量: '0' }] }), 'inline'),
      ruleset,
      runOptions(),
    )
    expect(issuesOf(zero, 'GP-002')[0]?.found).toContain('配置数量为 0')
  })

  it('warns in the reader when a quantity cell cannot be parsed', () => {
    const input = parseMaterial(JSON.stringify({ ...GOOD, rows: [{ 品名: '安全帽', 配置数量: '若干' }] }), 'inline')
    expect(input.warnings.join(' ')).toContain('无法解析为数字')
  })
})

describe('headcount reconciliation', () => {
  it('shows the multiplication it used', async () => {
    const ruleset = withConfiguration(await loadPack(), {
      'GP-003': { factors: [{ match: '绝缘手套', perPerson: 2, tolerance: 0 }] },
    })
    const material = JSON.stringify({ ...GOOD, rows: [{ 品名: '绝缘手套', 配置数量: '30' }] })
    const report = runCheck(parseMaterial(material, 'inline'), ruleset, runOptions())
    const issue = issuesOf(report, 'GP-003')[0]
    expect(issue?.found).toContain('20 人 × 每人 2')
    expect(issue?.found).toContain('应为 40')
  })

  it('honours the configured tolerance', async () => {
    const ruleset = withConfiguration(await loadPack(), {
      'GP-003': { factors: [{ match: '绝缘手套', perPerson: 2, tolerance: 5 }] },
    })
    const material = JSON.stringify({ ...GOOD, rows: [{ 品名: '绝缘手套', 配置数量: '36' }] })
    const report = runCheck(parseMaterial(material, 'inline'), ruleset, runOptions())
    expect(issuesOf(report, 'GP-003')).toHaveLength(0)
  })

  it('skips when the plan states no headcount', async () => {
    const ruleset = withConfiguration(await loadPack(), { 'GP-003': { factors: [{ match: '安全帽', perPerson: 1 }] } })
    const material = JSON.stringify({ rows: [{ 品名: '安全帽', 配置数量: '20' }] })
    const report = runCheck(parseMaterial(material, 'inline'), ruleset, runOptions())
    expect(report.skipped.find((entry) => entry.rule === 'GP-003')?.reason).toContain('未声明配置人数')
  })
})

describe('skipped reporting', () => {
  it('admits that the quantity factors are not configured', async () => {
    const report = await runFixture(JSON.stringify(GOOD), 'inline')
    expect(report.skipped.find((entry) => entry.rule === 'GP-003')?.reason).toContain('未配置 factors')
  })

  it('admits that the category list is not configured', async () => {
    const report = await runFixture(JSON.stringify(GOOD), 'inline')
    expect(report.skipped.find((entry) => entry.rule === 'GP-006')?.reason).toContain('requiredCategories')
  })

  it('admits that no plan period is declared', async () => {
    const material = JSON.stringify({ rows: [{ 品名: '安全帽', 配置数量: '20', 发放日期: '2026-03-05' }] })
    const report = await runFixture(material, 'inline')
    expect(report.skipped.find((entry) => entry.rule === 'GP-004')?.reason).toContain('配置期间')
  })

  it('names disabled rules exactly once and appends the configured note', async () => {
    const ruleset = await loadPack()
    const input = parseMaterial(JSON.stringify(GOOD), 'inline')
    const report = runCheck(input, ruleset, runOptions({ disabledRules: ['GP-005'], skipNotes: '本机构配备标准' }))
    const entries = report.skipped.filter((item) => item.rule === 'GP-005')
    expect(entries).toHaveLength(1)
    expect(entries[0]?.reason).toContain('禁用')
    expect(entries[0]?.reason).toContain('本机构配备标准')
  })
})

describe('report rendering', () => {
  it('never uses adjudicating wording and always carries the disclaimer', async () => {
    const material = await readFile(join(fixturesRoot, 'GP-003', 'GP-003-unsafe.json'), 'utf8')
    const cases = await readCases('GP-003')
    const report = await runFixture(material, 'GP-003-unsafe.json', cases.configure)
    const view = buildView(report)
    expect(findForbiddenWording(view.markdown)).toEqual([])
    expect(view.markdown).toContain('免责声明')
    expect(view.markdown).toContain('未执行的检查')
    expect(JSON.parse(view.reportJson)).toMatchObject({ plugin: pluginName, summary: report.summary })
  })
})

describe('plugin contract', () => {
  it('declares a static inject array covering every service apply touches', () => {
    expect(Array.isArray(inject)).toBe(true)
    expect(inject).toContain('tools')
  })

  it('exposes a Schemastery Config with serializable defaults', () => {
    const resolved = ConfigSchema(null)
    expect(resolved.rulesFile).toBe('rules/guard-plan-qc.yaml')
    expect(resolved.disabledRules).toEqual([])
    expect(resolved.timeoutMs).toBeGreaterThan(0)
  })

  it('resolves the packaged rule pack and rejects a missing one', () => {
    expect(resolvePackageFile('rules/guard-plan-qc.yaml')).toBe(rulesPath)
    expect(() => resolvePackageFile('rules/does-not-exist.yaml')).toThrow(/未找到/)
  })

  it('names the tool after the package family convention', () => {
    expect(TOOL_NAME).toBe('guard_plan_qc')
  })
})

describe('material reader', () => {
  it('rejects empty material instead of reporting an empty result', () => {
    expect(() => parseMaterial('   ', 'inline')).toThrow(/材料为空/)
  })

  it('rejects a table with no recognisable equipment columns', () => {
    expect(() => parseMaterial(JSON.stringify({ rows: [{ 备注: '甲' }] }), 'inline')).toThrow(/没有可识别的防护用品字段/)
  })
})

describe('shared kit', () => {
  it('parses wall-clock timestamps and rejects impossible dates', () => {
    expect(parseWallClock('2026-03-15')).toEqual({ date: '2026-03-15', time: '00:00', hasTime: false, minutes: 0 })
    expect(parseWallClock('2026-02-30')).toBeUndefined()
  })

  it('does calendar arithmetic', () => {
    expect(addDays('2026-03-31', 1)).toBe('2026-04-01')
    expect(diffDays('2026-03-01', '2026-03-06')).toBe(5)
  })

  it('reads the supported YAML subset and rejects the rest', () => {
    expect(parseYaml('a: 1\nb:\n  - x\n')).toEqual({ a: 1, b: ['x'] })
    expect(() => parseYaml('a: 1\na: 2\n')).toThrow(/duplicate/)
  })
})
