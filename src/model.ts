/**
 * Input contract for the protective-equipment configuration checker.
 *
 * The material is one 劳动防护用品配置表: the persons the plan covers, the products
 * it configures, and the issue log. The checker verifies that the plan is complete
 * and that its issue records are internally consistent — it never judges whether a
 * given product is the right protection for a given hazard, which is an
 * occupational-health judgement.
 */

/** One configured product row. */
export interface EquipmentRow {
  /** 1-based row number in the source. */
  row: number
  /** 品名. */
  name?: string
  /** 规格型号. */
  specification?: string
  /** 配置数量 as written. */
  quantity?: string
  /** 数量 as a number, when it parsed. */
  quantityValue?: number
  /** 单位. */
  unit?: string
  /** 配置标准/依据. */
  basis?: string
  /** 发放周期/更换周期 as written. */
  cycle?: string
  /** 发放日期. */
  issuedAt?: string
  /** 有效截止日期, when the plan states one. */
  expiresAt?: string
  /** 领用人. */
  receiver?: string
  /** Values keyed by the table's own column names. */
  fields: Record<string, string>
}

/** The whole normalized input. */
export interface GuardInput {
  target: string
  /** 工程/单位名称, when declared. */
  subject?: string
  /** 配置人数, when declared. */
  headcount?: number
  /** 配置期间起始日, when declared. */
  periodFrom?: string
  /** 配置期间结束日, when declared. */
  periodTo?: string
  rows: EquipmentRow[]
  /** Column names the reader saw, in order. */
  columns: string[]
  warnings: string[]
}

/** Column names recognised as each field, in priority order. */
export const COLUMNS = {
  name: ['品名', '名称', '防护用品名称', '劳动防护用品', 'name', 'product'],
  specification: ['规格型号', '规格', '型号', 'specification', 'spec'],
  quantity: ['配置数量', '数量', '发放数量', 'quantity', 'qty'],
  unit: ['单位', '计量单位', 'unit'],
  basis: ['配置标准', '配备标准', '标准依据', '依据', 'basis'],
  cycle: ['发放周期', '更换周期', '使用期限', '周期', 'cycle'],
  issuedAt: ['发放日期', '领用日期', '配置日期', 'issuedAt'],
  expiresAt: ['有效截止日期', '到期日期', '有效期至', 'expiresAt'],
  receiver: ['领用人', '使用人', '领用签字', 'receiver'],
} as const

/** Parse a quantity cell into a number, tolerating units and full-width digits. */
export function numberOf(raw: string | undefined): number | undefined {
  if (raw === undefined) return undefined
  const normalized = raw
    .replace(/[\uff10-\uff19]/g, (char) => String.fromCharCode(char.charCodeAt(0) - 0xfee0))
    .replace(/[,\s，]/g, '')
    .replace(/(套|件|个|双|顶|副|只|条|张|台|把|瓶|盒|付|支)$/, '')
  if (!/^[+-]?(?:\d+\.?\d*|\.\d+)$/.test(normalized)) return undefined
  return Number.parseFloat(normalized)
}
