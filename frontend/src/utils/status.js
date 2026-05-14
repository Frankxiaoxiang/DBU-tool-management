// utils/status.js — 状态映射单一来源，后续模块按需追加，禁止组件内硬编码

// ── 项目状态 ──────────────────────────────────────────
export const PROJECT_STATUS_MAP = {
  active:    { label: '进行中', type: 'success' },
  closed:    { label: '已关闭', type: 'info'    },
  cancelled: { label: '已作废', type: 'danger'  },
}

export function projectStatusTag(code) {
  return PROJECT_STATUS_MAP[code]?.type || 'info'
}

export function projectStatusLabel(code) {
  return PROJECT_STATUS_MAP[code]?.label || code
}

// ── 产品线 ──────────────────────────────────────────
export const PRODUCT_TYPE_MAP = {
  SUS_VC: 'SUS VC',
  CU_VC:  'Cu VC',
  HP:     'HP',
}

export function productTypeLabel(code) {
  return PRODUCT_TYPE_MAP[code] || code
}
