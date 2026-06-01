import { useEffect, useRef, useState } from 'react'
import styles from '../../styles/auth.module.css'

const GOOGLE_SCRIPT_ID = 'google-identity-services'
const GOOGLE_SCRIPT_SRC = 'https://accounts.google.com/gsi/client'

let googleScriptPromise

function loadGoogleScript() {
  if (window.google?.accounts?.id) {
    return Promise.resolve()
  }

  if (googleScriptPromise) {
    return googleScriptPromise
  }

  googleScriptPromise = new Promise((resolve, reject) => {
    const existingScript = document.getElementById(GOOGLE_SCRIPT_ID)
    if (existingScript) {
      existingScript.addEventListener('load', resolve, { once: true })
      existingScript.addEventListener('error', reject, { once: true })
      return
    }

    const script = document.createElement('script')
    script.id = GOOGLE_SCRIPT_ID
    script.src = GOOGLE_SCRIPT_SRC
    script.async = true
    script.defer = true
    script.onload = resolve
    script.onerror = () => reject(new Error('無法載入 Google 登入服務'))
    document.head.appendChild(script)
  })

  return googleScriptPromise
}

export default function GoogleAuthButton({ disabled, onCredential, mode = 'signin' }) {
  const buttonRef = useRef(null)
  const [scriptError, setScriptError] = useState('')
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID

  useEffect(() => {
    if (!clientId || disabled || !buttonRef.current) {
      return
    }

    let cancelled = false

    loadGoogleScript()
      .then(() => {
        if (cancelled || !buttonRef.current) return

        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (response) => {
            if (response?.credential) {
              onCredential(response.credential)
            }
          },
        })

        buttonRef.current.innerHTML = ''
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: 'outline',
          size: 'large',
          width: Math.min(buttonRef.current.offsetWidth || 320, 400),
          text: mode === 'signup' ? 'signup_with' : 'signin_with',
          locale: 'zh_TW',
        })
      })
      .catch(() => {
        if (!cancelled) {
          setScriptError('Google 登入服務載入失敗，請稍後再試')
        }
      })

    return () => {
      cancelled = true
    }
  }, [clientId, disabled, mode, onCredential])

  if (!clientId) {
    return (
      <button className={styles.googleBtn} type="button" disabled>
        尚未設定 Google 登入
      </button>
    )
  }

  return (
    <>
      <div
        className={styles.googleButtonWrapper}
        aria-disabled={disabled}
        ref={buttonRef}
      />
      {scriptError && <div className={styles.errorMsg}>{scriptError}</div>}
    </>
  )
}
