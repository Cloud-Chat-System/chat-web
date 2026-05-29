import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import Avatar from './Avatar'

describe('Avatar', () => {
  it('renders initials for a single-word name', () => {
    render(<Avatar name="alice" />)

    expect(screen.getByText('A')).toBeInTheDocument()
  })

  it('renders first and last initials for a multi-word name', () => {
    render(<Avatar name="Alice Chen" />)

    expect(screen.getByText('AC')).toBeInTheDocument()
  })

  it('renders image avatars with accessible alt text', () => {
    render(<Avatar name="Alice Chen" avatar="/avatars/alice.png" />)

    const image = screen.getByRole('img', { name: 'Alice Chen' })
    expect(image).toHaveAttribute('src', '/avatars/alice.png')
  })

  it('shows a status indicator when requested', () => {
    const { container } = render(<Avatar name="Alice" online showStatus />)

    expect(container.querySelector('span')).toBeInTheDocument()
  })
})
