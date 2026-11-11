'use client'

export function DemoLabel({ className = '' }: { className?: string }) {
  return (
    <span
      className={`font-mono text-[10px] tracking-widest uppercase px-1.5 py-0.5 ${className}`}
      style={{
        color: '#606060',
        border: '1px solid #262626',
        borderRadius: '2px',
      }}
    >
      SYNTHETIC
    </span>
  )
}
