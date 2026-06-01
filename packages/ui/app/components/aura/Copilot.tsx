// Presentational AI copilot rail. Stateless w.r.t. chat logic — the container
// passes `messages`, the in-progress `streaming` text, `isLoading`, and an
// `onSend` callback (wire it to your existing /api/v1/chat/stream handler).
import { useEffect, useRef, useState } from 'react';
import { Icon } from './icons';
import type { ChatMsg } from './types';

function fmt(t: string) {
  return t.split(/(\*\*[^*]+\*\*)/g).map((p, i) => (p.startsWith('**') ? <strong key={i}>{p.slice(2, -2)}</strong> : p));
}
function md(s: string) {
  return s.split('\n').map((line, i) =>
    line.startsWith('- ') ? (
      <div key={i} style={{ display: 'flex', gap: 7, padding: '2px 0', alignItems: 'flex-start', lineHeight: 1.5 }}>
        <span style={{ color: 'var(--accent-text)', flexShrink: 0 }}>•</span>
        <span style={{ flex: 1, minWidth: 0 }}>{fmt(line.slice(2))}</span>
      </div>
    ) : (
      <div key={i} style={{ minHeight: line ? 0 : 6, lineHeight: 1.5 }}>{fmt(line)}</div>
    )
  );
}
function clock(ts: string) {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

export function Copilot({ messages, streaming, isLoading, suggestions, onSend, onClear, sheetOpen, onCloseSheet }: {
  messages: ChatMsg[];
  streaming?: string;
  isLoading?: boolean;
  suggestions: string[];
  onSend: (text: string) => void;
  onClear?: () => void;
  sheetOpen?: boolean;
  onCloseSheet?: () => void;
}) {
  const [draft, setDraft] = useState('');
  const bodyRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [messages, streaming, isLoading]);

  const send = (text?: string) => {
    const q = (text ?? draft).trim();
    if (!q || isLoading) return;
    onSend(q);
    setDraft('');
    if (taRef.current) taRef.current.style.height = 'auto';
  };

  return (
    <aside className={`copilot ${sheetOpen ? 'sheet-open' : ''}`}>
      <div className="cp-head">
        <div className="cp-avatar"><Icon.Sparkle style={{ width: 17, height: 17, color: '#fff' }} /></div>
        <div style={{ flex: 1 }}>
          <div className="cp-name">Aura</div>
          <div className="cp-status"><span className="status-dot status-pulse" style={{ width: 6, height: 6 }}></span>Online · your daily agent</div>
        </div>
        {onClear && <button className="icon-btn" onClick={onClear} title="New chat"><Icon.Refresh /></button>}
        {onCloseSheet && <button className="icon-btn cp-sheet-close" onClick={onCloseSheet} title="Close" aria-label="Close"><Icon.ChevronDown /></button>}
      </div>

      <div className="cp-body scroll" ref={bodyRef}>
        {messages.map((m, i) => (
          <div className={`msg ${m.type} fade-in`} key={i}>
            <div className="bubble">{m.type === 'ai' ? md(m.message) : m.message}</div>
            <div className="msg-time">{clock(m.timestamp)}</div>
          </div>
        ))}
        {streaming ? (
          <div className="msg ai"><div className="bubble">{md(streaming)}</div></div>
        ) : isLoading ? (
          <div className="msg ai"><div className="bubble"><div className="typing"><span></span><span></span><span></span></div></div></div>
        ) : null}
      </div>

      {suggestions.length > 0 && (
        <div className="suggest-wrap">
          <div className="suggest-label">Suggested</div>
          <div className="suggest">
            {suggestions.map((s, i) => (
              <button className="suggest-btn" key={i} onClick={() => send(s)}><Icon.Sparkle />{s}</button>
            ))}
          </div>
        </div>
      )}

      <div className="composer">
        <div className="composer-box">
          <textarea
            ref={taRef}
            rows={1}
            placeholder="Ask Aura, or type / for commands…"
            value={draft}
            onChange={(e) => {
              setDraft(e.target.value);
              e.target.style.height = 'auto';
              e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
            }}
          />
          <button className="send-btn" onClick={() => send()} disabled={!draft.trim() || isLoading}><Icon.Send /></button>
        </div>
      </div>
    </aside>
  );
}
