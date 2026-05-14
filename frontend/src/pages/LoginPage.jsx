import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/useAuthStore'
import { validateEmail, validatePassword } from '../utils/validators'
import { FiEye, FiEyeOff, FiMessageCircle } from 'react-icons/fi'
import { FcGoogle } from 'react-icons/fc'
import styles from '../styles/auth.module.css'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const navigate = useNavigate()
  const { login, loginWithGoogle, isLoading, error, clearError } = useAuthStore()

  const handleSubmit = async (e) => {
    e.preventDefault()
    clearError()
    try {
      await login(email, password)
      navigate('/chat')
    } catch { /* error is set in store */ }
  }

  const handleGoogle = async () => {
    clearError()
    await loginWithGoogle()
    navigate('/chat')
  }

  return (
    <div className={styles.authContainer}>
      <div className={styles.authCard}>
        {/* Logo */}
        <div className={styles.logo}>
          <div className={styles.logoIcon}>
            <FiMessageCircle />
          </div>
          <h1 className={styles.logoTitle}>TSMC Messengehaha</h1>
          <p className={styles.logoSubtitle}>企業內部即時通訊系統</p>
        </div>

        {/* Error */}
        {error && <div className={styles.errorMsg}>{error}</div>}

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className={styles.formGroup}>
            <label className={styles.formLabel} htmlFor="login-email">Email</label>
            <input
              id="login-email"
              className={styles.formInput}
              type="email"
              placeholder="name@tsmc.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>

          <div className={styles.formGroup}>
            <label className={styles.formLabel} htmlFor="login-password">密碼</label>
            <div className={styles.inputWrapper}>
              <input
                id="login-password"
                className={styles.formInput}
                type={showPw ? 'text' : 'password'}
                placeholder="請輸入密碼"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
              <span
                className={styles.inputIcon}
                onClick={() => setShowPw(!showPw)}
                role="button"
                tabIndex={0}
                aria-label={showPw ? '隱藏密碼' : '顯示密碼'}
              >
                {showPw ? <FiEyeOff size={18} /> : <FiEye size={18} />}
              </span>
            </div>
          </div>

          <div className={styles.rememberRow}>
            <label className={styles.checkboxLabel}>
              <input type="checkbox" /> 記住我
            </label>
            <a href="#" className={styles.forgotLink}>忘記密碼？</a>
          </div>

          <button
            type="submit"
            className={styles.submitBtn}
            disabled={isLoading || !validateEmail(email) || !validatePassword(password)}
          >
            {isLoading ? (
              <span className={styles.btnLoading}>
                <span className={styles.spinner} />
                登入中...
              </span>
            ) : '登入'}
          </button>
        </form>

        <div className={styles.divider}>或</div>

        <button className={styles.googleBtn} onClick={handleGoogle} disabled={isLoading}>
          <FcGoogle size={20} />
          使用 Google 帳號登入
        </button>

        <p className={styles.switchLink}>
          還沒有帳號？<Link to="/register">立即註冊</Link>
        </p>
      </div>
    </div>
  )
}
