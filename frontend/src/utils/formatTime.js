import { formatDistanceToNow, format, isToday, isYesterday } from 'date-fns'
import { zhTW } from 'date-fns/locale/zh-TW'

export function formatMessageTime(timestamp) {
  const date = new Date(timestamp)
  return format(date, 'a h:mm', { locale: zhTW })
}

export function formatChatListTime(timestamp) {
  const date = new Date(timestamp)
  if (isToday(date)) {
    return format(date, 'a h:mm', { locale: zhTW })
  }
  if (isYesterday(date)) {
    return '昨天'
  }
  return formatDistanceToNow(date, { addSuffix: true, locale: zhTW })
}

export function formatDateDivider(timestamp) {
  const date = new Date(timestamp)
  if (isToday(date)) return '今天'
  if (isYesterday(date)) return '昨天'
  return format(date, 'yyyy年M月d日', { locale: zhTW })
}

export function shouldShowDateDivider(currentMsg, prevMsg) {
  if (!prevMsg) return true
  const curr = new Date(currentMsg.timestamp).toDateString()
  const prev = new Date(prevMsg.timestamp).toDateString()
  return curr !== prev
}
