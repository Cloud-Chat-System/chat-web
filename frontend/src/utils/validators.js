export function validateEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return re.test(email)
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
