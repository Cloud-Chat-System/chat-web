import PropTypes from 'prop-types'
import styles from '../../styles/components.module.css'

function getColorIndex(name) {
  let hash = 0
  for (const char of name) {
    hash = char.codePointAt(0) + ((hash << 5) - hash)
  }
  return Math.abs(hash) % 8
}

function getInitials(name) {
  if (!name) return '?'
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase()
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase()
}

function getSizeClass(size) {
  if (size === 'sm') return styles.avatarSm
  if (size === 'lg') return styles.avatarLg
  return styles.avatarMd
}

export default function Avatar({ name = '', avatar = null, size = 'md', online, showStatus = false }) {
  const sizeClass = getSizeClass(size)
  const bgClass = styles[`avatarBg${getColorIndex(name)}`]
  const hasAvatar = Boolean(avatar)
  const avatarClassName = `${styles.avatar} ${sizeClass} ${hasAvatar ? '' : bgClass}`
  const statusClassName = `${styles.onlineDot} ${size === 'sm' ? styles.onlineDotSmall : ''} ${
    online ? '' : styles.offlineDot
  }`

  return (
    <div className={avatarClassName}>
      {hasAvatar ? (
        <img src={avatar} alt={name} className={styles.avatarImg} />
      ) : (
        getInitials(name)
      )}
      {showStatus && (
        <span className={statusClassName} />
      )}
    </div>
  )
}

Avatar.propTypes = {
  name: PropTypes.string,
  avatar: PropTypes.string,
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  online: PropTypes.bool,
  showStatus: PropTypes.bool,
}
