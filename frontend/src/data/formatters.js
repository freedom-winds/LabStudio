export const statusText = {
  active: '进行中',
  ended: '已结束',
  open: '开启',
  archived: '归档',
  working: '工作中',
  ramping: '磨合中',
  completed: '完成',
  abandoned: '放弃',
  todo: '未开始',
  doing: '进行中',
  done: '已完成',
  pending: '待审批',
  approved: '已通过',
  rejected: '已拒绝',
  cancelled: '已取消',
  disabled: '已禁用',
  deleted: '已删除',
}

export const roleText = {
  admin: '系统管理员',
  teacher: '教师',
  student: '学生',
  year_admin: '年度管理员',
  leader: '队伍领队',
  member: '队伍成员',
  manager: '实验管理者',
  participant: '实验参与者',
  observer: '实验观察者',
}

export function humanStatus(value) {
  return statusText[value] || value || '-'
}

export function humanRole(value) {
  return roleText[value] || value || '-'
}

export function formatDate(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

export function shortDate(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('zh-CN')
}

export function fileSize(bytes = 0) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let index = 0
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024
    index += 1
  }
  return `${size.toFixed(index ? 1 : 0)} ${units[index]}`
}
