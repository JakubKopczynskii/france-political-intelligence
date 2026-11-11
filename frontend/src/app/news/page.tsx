'use client'

import { useEffect, useState, useCallback } from 'react'
import { RefreshCw, ExternalLink, X } from 'lucide-react'
import { api } from '@/lib/api'
import type { Article } from '@/lib/types'
import { Header } from '@/components/layout/Header'
import { InfoTypeLabel } from '@/components/ui/InfoTypeLabel'

const TOPICS = ['All', 'politics', 'fiscal', 'ecb', 'energy', 'defence', 'trade', 'macro', 'companies']

function Spinner() {
  return (
    <div
      className="sys-spin"
      style={{
        width: 12,
        height: 12,
        borderRadius: '50%',
        border: '1px solid #262626',
        borderTopColor: '#929292',
        display: 'inline-block',
      }}
    />
  )
}

export default function NewsPage() {
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [topic, setTopic] = useState('All')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Article | null>(null)
  const [connected, setConnected] = useState(true)

  const load = useCallback((topicFilter: string) => {
    setLoading(true)
    const t = topicFilter !== 'All' ? topicFilter : undefined
    api
      .getNews({ topic: t, limit: 100 })
      .then((data) => {
        setArticles(data)
        setConnected(true)
        setError(null)
      })
      .catch((e: unknown) => {
        setError(String(e))
        setConnected(false)
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load('All') }, [load])

  const handleTopic = (t: string) => {
    setTopic(t)
    load(t)
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await api.refreshFeeds()
      load(topic)
    } catch (e: unknown) {
      setError(String(e))
    } finally {
      setRefreshing(false)
    }
  }

  const filtered = articles.filter((a) =>
    search ? a.title.toLowerCase().includes(search.toLowerCase()) : true
  )

  return (
    <div className="flex flex-col h-full">
      <Header title="News Intelligence" isConnected={connected} />

      <div className="flex-1 p-6 overflow-auto">
        {error && (
          <div className="mb-4 font-mono text-[11px] px-3 py-2" style={{ color: '#FF3B30', border: '1px solid #2a1a1a' }}>
            {error}
          </div>
        )}

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <div className="flex flex-wrap gap-1">
            {TOPICS.map((t) => (
              <button
                key={t}
                onClick={() => handleTopic(t)}
                className="font-mono text-[10px] tracking-wide uppercase px-2 py-1 transition-colors"
                style={{
                  color: topic === t ? '#F5F5F5' : '#606060',
                  border: `1px solid ${topic === t ? '#606060' : '#262626'}`,
                  borderRadius: '2px',
                  background: 'transparent',
                }}
              >
                {t}
              </button>
            ))}
          </div>
          <input
            type="text"
            placeholder="SEARCH HEADLINES"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 min-w-48 font-mono text-[11px] px-3 py-1.5 outline-none"
            style={{
              background: '#101010',
              border: '1px solid #262626',
              borderRadius: '2px',
              color: '#F5F5F5',
            }}
          />
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-1.5 font-mono text-[10px] tracking-wide uppercase px-3 py-1.5 transition-opacity disabled:opacity-40"
            style={{
              color: '#F5F5F5',
              border: '1px solid #262626',
              borderRadius: '2px',
              background: 'transparent',
            }}
          >
            <RefreshCw size={10} className={refreshing ? 'sys-spin' : ''} />
            SCAN FEEDS
          </button>
        </div>

        {loading ? (
          <div className="flex items-center gap-2 py-8" style={{ color: '#606060' }}>
            <Spinner />
            <span className="font-mono text-[11px] tracking-widest uppercase">SCANNING</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="font-mono text-[11px] py-8" style={{ color: '#3a3a3a' }}>
            NO ARTICLES — SCAN FEEDS TO INGEST
          </div>
        ) : (
          <div className="space-y-0">
            {filtered.map((a) => {
              const impLabel = a.importance_label ?? 'LOW'
              const impColor = impLabel === 'HIGH' ? '#FF9500' : impLabel === 'MEDIUM' ? '#929292' : '#3a3a3a'
              return (
                <div
                  key={a.id}
                  className="flex gap-3 cursor-pointer"
                  onClick={() => setSelected(a)}
                  style={{ borderBottom: '1px solid #1a1a1a', paddingTop: 12, paddingBottom: 12 }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = '#101010')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  {/* Article thumbnail */}
                  <div
                    style={{
                      width: 72,
                      height: 54,
                      flexShrink: 0,
                      background: '#0d0d0d',
                      border: '1px solid #1a1a1a',
                      overflow: 'hidden',
                    }}
                  >
                    {a.image_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={a.image_url}
                        alt=""
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                        loading="lazy"
                        onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                      />
                    ) : (
                      <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <span style={{ fontFamily: 'monospace', fontSize: 8, color: '#262626' }}>NO IMG</span>
                      </div>
                    )}
                  </div>

                  {/* Article content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className="font-mono text-[9px] tracking-widest uppercase px-1.5 py-0.5"
                        style={{ color: impColor, border: `1px solid ${impColor}22` }}
                      >
                        {impLabel}
                      </span>
                      <span className="font-mono text-[10px]" style={{ color: '#3a3a3a' }}>
                        {a.published_at ? new Date(a.published_at).toLocaleDateString('fr-FR') : '—'}
                      </span>
                      <span className="font-mono text-[10px]" style={{ color: '#3a3a3a' }}>·</span>
                      <span className="font-mono text-[10px]" style={{ color: '#606060' }}>{a.source_name}</span>
                    </div>
                    <div className="text-[13px] line-clamp-2 mb-1.5" style={{ color: '#F5F5F5', lineHeight: 1.4 }}>
                      {a.title}
                    </div>
                    {a.ai?.summary && (
                      <div className="text-[11px] mb-1.5 line-clamp-1" style={{ color: '#929292' }}>
                        <span className="font-mono text-[9px] mr-1.5" style={{ color: '#606060' }}>AI</span>
                        {a.ai.summary}
                      </div>
                    )}
                    <div className="flex gap-1 flex-wrap items-center">
                      {a.topic_tags?.slice(0, 3).map((tag) => (
                        <span key={tag} className="font-mono text-[9px] tracking-wide uppercase px-1 py-0.5" style={{ color: '#606060', border: '1px solid #1a1a1a' }}>
                          {tag}
                        </span>
                      ))}
                      <InfoTypeLabel type={a.information_type} />
                    </div>
                  </div>

                  <a
                    href={a.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    style={{ color: '#3a3a3a', flexShrink: 0, alignSelf: 'center' }}
                  >
                    <ExternalLink size={12} />
                  </a>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Detail modal */}
      {selected && (
        <div
          className="fixed inset-0 flex items-center justify-center z-50 p-4"
          style={{ background: 'rgba(0,0,0,0.8)' }}
          onClick={() => setSelected(null)}
        >
          <div
            className="w-full max-w-2xl max-h-[80vh] overflow-auto p-6"
            style={{ background: '#101010', border: '1px solid #262626' }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal image */}
            {selected.image_url && (
              <div style={{ margin: '-24px -24px 20px', height: 180, overflow: 'hidden', position: 'relative' }}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={selected.image_url}
                  alt={selected.title}
                  style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'brightness(0.6)' }}
                  onError={(e) => { (e.target as HTMLImageElement).parentElement!.style.display = 'none' }}
                />
              </div>
            )}
            <div className="flex items-start justify-between gap-3 mb-4">
              <h2 className="text-[15px] font-medium leading-snug" style={{ color: '#F5F5F5' }}>
                {selected.title}
              </h2>
              <button onClick={() => setSelected(null)} style={{ color: '#606060' }}>
                <X size={16} />
              </button>
            </div>
            <div className="flex flex-wrap gap-2 mb-4">
              <InfoTypeLabel type={selected.information_type} />
              {selected.is_synthetic && (
                <span className="font-mono text-[10px] tracking-widest uppercase px-1.5 py-0.5" style={{ color: '#606060', border: '1px solid #262626' }}>
                  SYNTHETIC
                </span>
              )}
            </div>
            <p className="text-[13px] mb-5" style={{ color: '#929292', lineHeight: '1.6' }}>
              {selected.content_snippet}
            </p>
            {selected.ai && (
              <div className="mb-5 p-3" style={{ border: '1px solid #1a1a1a' }}>
                <div className="font-mono text-[9px] tracking-widest mb-2" style={{ color: '#606060' }}>
                  AI EXTRACTION · MARKET RELEVANCE {(selected.ai.market_relevance ?? '—').toUpperCase()} · VERIFY AGAINST SOURCE
                </div>
                {selected.ai.summary && <div className="text-[12px] mb-2" style={{ color: '#F5F5F5' }}>{selected.ai.summary}</div>}
                {selected.ai.scenario_signals && (
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                    {Object.entries(selected.ai.scenario_signals).map(([k, v]) => (
                      <div key={k} className="flex items-center gap-2 font-mono text-[9px]">
                        <span className="w-28" style={{ color: '#606060' }}>{k.replace('_', ' ').toUpperCase()}</span>
                        <div style={{ flex: 1, height: 2, background: '#1a1a1a' }}>
                          <div style={{ width: `${Math.min(Number(v) || 0, 1) * 100}%`, height: '100%', background: '#929292' }} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            <div className="grid grid-cols-2 gap-4 font-mono text-[11px]">
              <div>
                <div className="mb-1" style={{ color: '#606060' }}>SOURCE</div>
                <div style={{ color: '#F5F5F5' }}>{selected.source_name}</div>
              </div>
              <div>
                <div className="mb-1" style={{ color: '#606060' }}>PUBLISHED</div>
                <div style={{ color: '#F5F5F5' }}>
                  {selected.published_at ? new Date(selected.published_at).toLocaleString() : '—'}
                </div>
              </div>
              <div>
                <div className="mb-1" style={{ color: '#606060' }}>ENTITIES</div>
                <div style={{ color: '#F5F5F5' }}>{selected.entities?.join(', ') || '—'}</div>
              </div>
              <div>
                <div className="mb-1" style={{ color: '#606060' }}>SECTORS</div>
                <div style={{ color: '#F5F5F5' }}>{selected.affected_sectors?.join(', ') || '—'}</div>
              </div>
            </div>
            <a
              href={selected.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 inline-flex items-center gap-1 font-mono text-[11px] tracking-wide"
              style={{ color: '#929292' }}
            >
              <ExternalLink size={10} /> VIEW SOURCE
            </a>
          </div>
        </div>
      )}
    </div>
  )
}
