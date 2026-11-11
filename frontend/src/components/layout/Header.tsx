'use client'

export function Header({
  title,
  lastRefresh,
  isConnected,
  showDemoLabel,
}: {
  title: string
  lastRefresh?: string | null
  isConnected?: boolean
  showDemoLabel?: boolean
}) {
  const connected = isConnected !== false

  return (
    <header
      className="flex items-center justify-between px-6 flex-shrink-0"
      style={{
        height: '48px',
        borderBottom: '1px solid #262626',
        background: '#090909',
      }}
    >
      <div className="flex items-center gap-4">
        <span
          className="font-mono text-[10px] tracking-widest uppercase"
          style={{ color: '#606060' }}
        >
          INTEL
        </span>
        <span
          className="text-[11px]"
          style={{ color: '#262626' }}
        >
          /
        </span>
        <h1 className="text-[13px] font-medium" style={{ color: '#F5F5F5' }}>
          {title}
        </h1>
        {showDemoLabel && (
          <span
            className="font-mono text-[10px] tracking-widest uppercase px-2 py-0.5"
            style={{
              color: '#606060',
              border: '1px solid #262626',
              borderRadius: '2px',
            }}
          >
            SYNTHETIC
          </span>
        )}
      </div>

      <div className="flex items-center gap-4">
        {lastRefresh && (
          <span className="font-mono text-[10px]" style={{ color: '#606060' }}>
            {new Date(lastRefresh).toLocaleTimeString()}
          </span>
        )}
        <div className="flex items-center gap-1.5">
          <div
            className={connected ? 'sys-pulse' : ''}
            style={{
              width: '4px',
              height: '4px',
              borderRadius: '50%',
              background: connected ? '#F5F5F5' : '#3a3a3a',
            }}
          />
          <span className="font-mono text-[10px]" style={{ color: '#606060' }}>
            {connected ? 'SYS OK' : 'OFFLINE'}
          </span>
        </div>
      </div>
    </header>
  )
}
