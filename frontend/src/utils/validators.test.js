import { describe, expect, it } from 'vitest'

import {
  validateEmail,
  validateName,
  validatePassword,
  validatePasswordMatch,
} from './validators'

describe('validators', () => {
  it('accepts syntactically valid email addresses', () => {
    expect(validateEmail('alice@example.com')).toBe(true)
    expect(validateEmail('bob.lin@tsmc.com')).toBe(true)
  })

  it('rejects invalid email addresses', () => {
    expect(validateEmail('alice')).toBe(false)
    expect(validateEmail('alice@example')).toBe(false)
    expect(validateEmail('alice example.com')).toBe(false)
  })

  it('requires passwords to be at least six characters', () => {
    expect(validatePassword('12345')).toBe(false)
    expect(validatePassword('123456')).toBe(true)
  })

  it('requires trimmed display names to have at least two characters', () => {
    expect(validateName(' A ')).toBe(false)
    expect(validateName(' Alice ')).toBe(true)
  })

  it('checks password confirmation exactly', () => {
    expect(validatePasswordMatch('password123', 'password123')).toBe(true)
    expect(validatePasswordMatch('password123', 'Password123')).toBe(false)
  })
})
