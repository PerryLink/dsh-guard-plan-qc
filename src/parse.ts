/**
 * Reader for the protective-equipment configuration table.
 *
 * The material is JSON or YAML with a `rows` list, each row a mapping of the
 * table's own column names, plus optional plan-level fields.
 */

import { YamlSubsetError, parseYaml } from './shared/yaml.ts'
import { COLUMNS, numberOf } from './model.ts'
import type { EquipmentRow, GuardInput } from './model.ts'

/** Raised when the material cannot be read at all. */
export class MaterialError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'MaterialError'
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function text(value: unknown): string | undefined {
  if (value === undefined || value === null) return undefined
  if (typeof value === 'string') return value.trim() === '' ? undefined : value.trim()
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  return undefined
}

/** Find the first present value among a set of candidate column names. */
function pick(fields: Record<string, string>, names: readonly string[]): string | undefined {
  const normalize = (value: string): string => value.toLowerCase().replace(/[\s\u3000_-]/g, '')
  for (const name of names) {
    const direct = fields[name]
    if (direct !== undefined && direct !== '') return direct
    const loose = Object.keys(fields).find((key) => normalize(key) === normalize(name))
    if (loose !== undefined) {
      const value = fields[loose]
      if (value !== undefined && value !== '') return value
    }
  }
  return undefined
}

function parseRow(raw: unknown, index: number): EquipmentRow {
  if (!isRecord(raw)) throw new MaterialError(`rows[${index}] 必须是映射`)
  const fields: Record<string, string> = {}
  for (const [key, value] of Object.entries(raw)) {
    if (value === undefined || value === null) continue
    const rendered = typeof value === 'string' ? value.trim() : text(value)
    fields[key] = rendered ?? ''
  }
  const row: EquipmentRow = { row: index + 1, fields }
  const declared = text(raw.row)
  if (declared !== undefined && /^\d+$/.test(declared)) row.row = Number.parseInt(declared, 10)

  for (const [field, names] of Object.entries(COLUMNS) as [keyof typeof COLUMNS, readonly string[]][]) {
    const value = pick(fields, names)
    if (value === undefined) continue
    row[field] = value
  }
  const quantity = numberOf(row.quantity)
  if (quantity !== undefined) row.quantityValue = quantity
  return row
}

/**
 * Parse material into the normalized input contract.
 * @param source - JSON or YAML text.
 * @param target - description of where the material came from.
 * @returns the normalized input.
 */
export function parseMaterial(source: string, target: string): GuardInput {
  const trimmed = source.trim()
  if (trimmed === '') throw new MaterialError('材料为空')
  let document: unknown
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    try {
      document = JSON.parse(trimmed)
    } catch (error) {
      throw new MaterialError(`JSON 无法解析：${error instanceof Error ? error.message : String(error)}`)
    }
  } else {
    try {
      document = parseYaml(trimmed)
    } catch (error) {
      if (error instanceof YamlSubsetError) throw new MaterialError(`YAML 无法解析：${error.message}`)
      throw error
    }
  }

  const warnings: string[] = []
  let list: unknown
  let subject: string | undefined
  let headcount: number | undefined
  let periodFrom: string | undefined
  let periodTo: string | undefined
  if (Array.isArray(document)) {
    list = document
  } else if (isRecord(document)) {
    list = document.rows ?? document.items ?? document.配置表
    subject = text(document.subject ?? document.工程名称 ?? document.单位名称)
    headcount = numberOf(text(document.headcount ?? document.配置人数))
    periodFrom = text(document.periodFrom ?? document.配置期间起)
    periodTo = text(document.periodTo ?? document.配置期间止)
  } else {
    throw new MaterialError('材料根节点必须是映射或列表')
  }

  if (list === undefined || list === null) throw new MaterialError('材料缺少 rows 列表，无法执行检查')
  if (!Array.isArray(list)) throw new MaterialError('rows 必须是列表')
  if (list.length === 0) throw new MaterialError('rows 为空列表，无法执行检查')

  const rows = list.map((entry, index) => parseRow(entry, index))
  const columns = [...new Set(rows.flatMap((row) => Object.keys(row.fields)))]
  const normalize = (value: string): string => value.toLowerCase().replace(/[\s\u3000_-]/g, '')
  const known = new Set(Object.values(COLUMNS).flat().map(normalize))
  if (!columns.some((column) => known.has(normalize(column)))) {
    throw new MaterialError(
      `材料中没有可识别的防护用品字段，已识别的列名为：${columns.join(' / ') || '（无）'}；` +
        `请至少提供以下之一：${[...COLUMNS.name, ...COLUMNS.quantity, ...COLUMNS.issuedAt].join(' / ')}`,
    )
  }

  const input: GuardInput = { target, rows, columns, warnings }
  if (subject !== undefined) input.subject = subject
  if (headcount !== undefined) input.headcount = headcount
  if (periodFrom !== undefined) input.periodFrom = periodFrom
  if (periodTo !== undefined) input.periodTo = periodTo

  const unparsed = rows.filter((row) => row.quantity !== undefined && row.quantityValue === undefined)
  if (unparsed.length > 0) {
    warnings.push(`有 ${unparsed.length} 行的配置数量无法解析为数字，这些行不参与数量核对`)
  }
  if (headcount === undefined) warnings.push('材料未声明配置人数（headcount），按人数推算数量的检查将无法执行')
  return input
}
