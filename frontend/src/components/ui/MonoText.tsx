import React from 'react'

interface MonoTextProps {
  children: React.ReactNode
  className?: string
  as?: 'span' | 'code' | 'p' | 'div'
}

/** Wraps text in JetBrains Mono. Use for IDs, hashes, IPs, timestamps, code. */
export const MonoText: React.FC<MonoTextProps> = ({ children, className = '', as: Tag = 'span' }) => (
  <Tag className={`font-mono-data text-2xs ${className}`}>{children}</Tag>
)
