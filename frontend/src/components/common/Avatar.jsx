import styles from '../../styles/components.module.css'

function getColorIndex(name) {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return Math.abs(hash) % 8
}

function getInitials(name) {
  if (!name) return '?'
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase()
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase()
}

export default function Avatar({ name = '', avatar = null, size = 'md', online, showStatus = false }) {
  const sizeClass = size === 'sm' ? styles.avatarSm : size === 'lg' ? styles.avatarLg : styles.avatarMd
  const bgClass = styles[`avatarBg${getColorIndex(name)}`]

  return (
    <div className={`${styles.avatar} ${sizeClass} ${!avatar ? bgClass : ''}`}>
      {avatar ? (
        <img src={avatar} alt={name} className={styles.avatarImg} />
      ) : (
        getInitials(name)
      )}
      {showStatus && (
        <span
          className={`${styles.onlineDot} ${size === 'sm' ? styles.onlineDotSmall : ''} ${!online ? styles.offlineDot : ''
            }`}
        />
      )}
    </div>
  )
}
