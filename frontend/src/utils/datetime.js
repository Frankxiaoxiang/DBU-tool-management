import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'
import customParseFormat from 'dayjs/plugin/customParseFormat'

dayjs.extend(utc)
dayjs.extend(timezone)
dayjs.extend(customParseFormat)
dayjs.tz.setDefault('Asia/Shanghai')

export function parseBackendTime(str) {
  if (!str) return null
  return dayjs.tz(str)
}

export function formatBackendTime(str, fmt = 'YYYY-MM-DD HH:mm') {
  const t = parseBackendTime(str)
  return t ? t.format(fmt) : '-'
}

export function formatDate(str, fmt = 'YYYY-MM-DD') {
  return formatBackendTime(str, fmt)
}
