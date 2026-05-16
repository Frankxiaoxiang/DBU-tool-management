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

// ── 批次状态 ──────────────────────────────────────────
export const BATCH_STATUS_MAP = {
  draft:       { label: '草稿',  type: 'info'    },
  in_progress: { label: '进行中', type: 'warning' },
  completed:   { label: '已完成', type: 'success' },
  cancelled:   { label: '已作废', type: 'danger'  },
}

export function batchStatusTag(code) {
  return BATCH_STATUS_MAP[code]?.type || 'info'
}

export function batchStatusLabel(code) {
  return BATCH_STATUS_MAP[code]?.label || code
}

// ── 批次类型 ──────────────────────────────────────────
export const BATCH_TYPE_MAP = {
  manual_init:    { label: '手动初版',  type: 'primary' },
  mass_prod:      { label: '量产',      type: 'success' },
  addon_quantity: { label: '加开-加量', type: 'warning' },
  addon_optimize: { label: '加开-优化', type: 'info'    },
}

export function batchTypeTag(code) {
  return BATCH_TYPE_MAP[code]?.type || 'info'
}

export function batchTypeLabel(code) {
  return BATCH_TYPE_MAP[code]?.label || code
}

// ===== Fixture 治具状态（Phase 2 Step 2-2-1）=====

export const FIXTURE_STATUS_MAP = {
  pending_iqc:         { label: '待IQC检验',     type: 'warning' },
  iqc_inspecting:      { label: 'IQC检验中',     type: 'warning' },
  emergency_pending:   { label: '紧急上机待确认',  type: 'danger'  },
  concession_accepted: { label: '让步接受',       type: 'warning' },
  installing:          { label: '安装调试中',     type: 'warning' },
  acceptance_testing:  { label: '试产验收中',     type: 'warning' },
  in_stock:            { label: '在库',           type: 'success' },
  in_use:              { label: '使用中',         type: 'success' },
  maintaining:         { label: '保养中',         type: 'info'    },
  repairing:           { label: '维修中',         type: 'danger'  },
  sealed:              { label: '已封存',         type: 'info'    },
  scrapped:            { label: '已报废',         type: 'danger'  },
}

export function fixtureStatusLabel(status) {
  return FIXTURE_STATUS_MAP[status]?.label || status
}

export function fixtureStatusType(status) {
  return FIXTURE_STATUS_MAP[status]?.type || 'info'
}
