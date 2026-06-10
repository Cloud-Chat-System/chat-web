import { formatDistanceToNow, format, isToday, isYesterday } from 'date-fns'
import { zhTW } from 'date-fns/locale/zh-TW'

const TIMEZONE_SUFFIX_PATTERN = /(?:Z|[+-]\d{2}:?\d{2})$/i

export function parseBackendTimestamp(timestamp) {
  if (typeof timestamp !== 'string') {
    return new Date(timestamp)
  }

  const normalizedTimestamp = TIMEZONE_SUFFIX_PATTERN.test(timestamp)
    ? timestamp
    : `${timestamp}Z`

  return new Date(normalizedTimestamp)
}

export function formatMessageTime(timestamp) {
  const date = parseBackendTimestamp(timestamp)
  return format(date, 'a h:mm', { locale: zhTW })
}

export function formatChatListTime(timestamp) {
  const date = parseBackendTimestamp(timestamp)
  if (isToday(date)) {
    return format(date, 'a h:mm', { locale: zhTW })
  }
  if (isYesterday(date)) {
    return '昨天'
  }
  return formatDistanceToNow(date, { addSuffix: true, locale: zhTW })
}

export function formatDateDivider(timestamp) {
  const date = parseBackendTimestamp(timestamp)
  if (isToday(date)) return '今天'
  if (isYesterday(date)) return '昨天'
  return format(date, 'yyyy年M月d日', { locale: zhTW })
}

export function shouldShowDateDivider(currentMsg, prevMsg) {
  if (!prevMsg) return true
  const curr = parseBackendTimestamp(currentMsg.timestamp).toDateString()
  const prev = parseBackendTimestamp(prevMsg.timestamp).toDateString()
  return curr !== prev
}
