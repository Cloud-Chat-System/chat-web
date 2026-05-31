import { useState } from 'react'
import PropTypes from 'prop-types'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/useAuthStore'
import {
  validateEmail,
  validatePassword,
  validateName,
  validatePasswordMatch,
} from '../utils/validators'
import { FiEye, FiEyeOff, FiMessageCircle, FiCheck, FiX } from 'react-icons/fi'
import styles from '../styles/auth.module.css'

function ValidationIcon({ valid, show }) {
  if (!show) return null
  return valid ? (
    <span className={`${styles.inputIcon} ${styles.validIcon}`}><FiCheck size={16} /></span>
  ) : (
    <span className={`${styles.inputIcon} ${styles.invalidIcon}`}><FiX size={16} /></span>
  )
}

ValidationIcon.propTypes = {
  valid: PropTypes.bool.isRequired,
  show: PropTypes.bool.isRequired,
}

export default function RegisterPage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPw, setConfirmPw] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [success, setSuccess] = useState(false)
  const navigate = useNavigate()
  const { register, isLoading, error, clearError } = useAuthStore()

  const isValid =
    validateName(name) &&
    validateEmail(email) &&
    validatePassword(password) &&
    validatePasswordMatch(password, confirmPw)

  const handleSubmit = async (e) => {
    e.preventDefault()
    clearError()
    try {
      await register(name, email, password)
      setSuccess(true)
      setTimeout(() => navigate('/login'), 1500)
    } catch { /* error is set in store */ }
  }

  return (
    <div className={styles.authContainer}>
      <div className={styles.authCard}>
        <div className={styles.logo}>
          <div className={styles.logoIcon}>
            <FiMessageCircle />
          </div>
          <h1 className={styles.logoTitle}>建立帳號</h1>
          <p className={styles.logoSubtitle}>加入 TSMC Messenger</p>
        </div>

        {error && <div className={styles.errorMsg}>{error}</div>}
        {success && <div className={styles.successMsg}>註冊成功！正在跳轉至登入頁面...</div>}

        <form onSubmit={handleSubmit}>
          <div className={styles.formGroup}>
            <label className={styles.formLabel} htmlFor="reg-name">使用者名稱</label>
            <div className={styles.inputWrapper}>
              <input
                id="reg-name"
                data-testid="register-name"
                className={styles.formInput}
                type="text"
                placeholder="請輸入名稱"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
              <ValidationIcon valid={validateName(name)} show={name.length > 0} />
            </div>
          </div>

          <div className={styles.formGroup}>
            <label className={styles.formLabel} htmlFor="reg-email">Email</label>
            <div className={styles.inputWrapper}>
              <input
                id="reg-email"
                data-testid="register-email"
                className={styles.formInput}
                type="email"
                placeholder="name@tsmc.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
              <ValidationIcon valid={validateEmail(email)} show={email.length > 0} />
            </div>
          </div>

          <div className={styles.formGroup}>
            <label className={styles.formLabel} htmlFor="reg-password">密碼</label>
            <div className={styles.inputWrapper}>
              <input
                id="reg-password"
                data-testid="register-password"
                className={styles.formInput}
                type={showPw ? 'text' : 'password'}
                placeholder="至少 6 個字元"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
                required
              />
              <button
                type="button"
                className={styles.inputIcon}
                onClick={() => setShowPw(!showPw)}
                aria-label={showPw ? '隱藏密碼' : '顯示密碼'}
              >
                {showPw ? <FiEyeOff size={18} /> : <FiEye size={18} />}
              </button>
            </div>
          </div>

          <div className={styles.formGroup}>
            <label className={styles.formLabel} htmlFor="reg-confirm">確認密碼</label>
            <div className={styles.inputWrapper}>
              <input
                id="reg-confirm"
                data-testid="register-confirm-password"
                className={styles.formInput}
                type={showPw ? 'text' : 'password'}
                placeholder="再次輸入密碼"
                value={confirmPw}
                onChange={(e) => setConfirmPw(e.target.value)}
                autoComplete="new-password"
                required
              />
              <ValidationIcon
                valid={validatePasswordMatch(password, confirmPw)}
                show={confirmPw.length > 0}
              />
            </div>
          </div>

          <button
            type="submit"
            data-testid="register-submit"
            className={styles.submitBtn}
            disabled={isLoading || !isValid}
            style={{ marginTop: 8 }}
          >
            {isLoading ? (
              <span className={styles.btnLoading}>
                <span className={styles.spinner} />
                <span>註冊中...</span>
              </span>
            ) : '建立帳號'}
          </button>
        </form>

        <p className={styles.switchLink}>
          已有帳號？<Link to="/login">立即登入</Link>
        </p>
      </div>
    </div>
  )
}
