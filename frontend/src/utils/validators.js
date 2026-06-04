export function validateEmail(email) {
  if (typeof email !== 'string' || email.length === 0 || email.length > 254) {
    return false
  }

  const whitespace = [' ', '\t', '\n', '\r', '\f', '\v']
  if (whitespace.some((char) => email.includes(char))) {
    return false
  }

  const atIndex = email.indexOf('@')
  if (atIndex <= 0 || atIndex !== email.lastIndexOf('@')) {
    return false
  }

  const domain = email.slice(atIndex + 1)
  if (!domain.includes('.') || domain.startsWith('.') || domain.endsWith('.')) {
    return false
  }

  return domain.split('.').every((part) => part.length > 0)
}

export function validatePassword(password) {
  return password.length >= 6
}

export function validateName(name) {
  return name.trim().length >= 2
}

export function validatePasswordMatch(password, confirm) {
  return password === confirm
}
