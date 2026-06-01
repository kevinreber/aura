// Presentational Aura widgets — consume view-model props from `types.ts`.
import { useState } from 'react';
import { Icon, type IconName } from './icons';
import type {
  WeatherVM, MarketsVM, EventVM, TaskVM, TomorrowVM, CommuteVM, HabitVM, NoteVM,
} from './types';

export function Spark({ data, color }: { data: number[]; color: string }) {
  const w = 54, h = 22, pad = 2;
  const min = Math.min(...data), max = Math.max(...data);
  const span = max - min || 1;
  const pts = data.map((d, i) => {
    const x = pad + (i / (data.length - 1)) * (w - pad * 2);
    const y = h - pad - ((d - min) / span) * (h - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return (
    <svg className="spark" viewBox={`0 0 ${w} ${h}`} fill="none">
      <polyline points={pts} stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function CardHead({ icon, title, meta }: { icon: IconName; title: string; meta?: React.ReactNode }) {
  const Ic = Icon[icon];
  return (
    <div className="card-head">
      <div className="card-ic"><Ic /></div>
      <span className="card-title">{title}</span>
      <div className="card-meta">{meta}</div>
    </div>
  );
}

export function WeatherCard({ wx, className }: { wx: WeatherVM; className?: string }) {
  return (
    <div className={`card ${className || ''}`}>
      <CardHead icon="CloudSun" title="Weather" meta={<span className="chip">{wx.location.split(',')[0]}</span>} />
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <div className="wx-temp">{Math.round(wx.current_temp)}°</div>
          <div className="wx-cond">{wx.condition}</div>
        </div>
        <div style={{ color: 'var(--accent-text)', opacity: 0.7 }}><Icon.CloudSun style={{ width: 46, height: 46 }} /></div>
      </div>
      <div className="wx-row">
        <div className="wx-stat"><span className="k">High</span><span className="v">{Math.round(wx.temp_hi)}°</span></div>
        <div className="wx-stat"><span className="k">Low</span><span className="v">{Math.round(wx.temp_lo)}°</span></div>
        <div className="wx-stat"><span className="k">Rain</span><span className="v">{wx.precip_chance}%</span></div>
        {wx.wind > 0 && <div className="wx-stat"><span className="k">Wind</span><span className="v">{wx.wind} mph</span></div>}
      </div>
    </div>
  );
}

const RANGE_LABEL: Record<string, string> = { '1D': '1D', '1W': '1W', '30D': '30D', '90D': '90D', '1Y': '1Y' };
export function MarketsCard({ mkt, className, expanded, range: rangeProp, onRange }: {
  mkt: MarketsVM; className?: string; expanded?: boolean; range?: string; onRange?: (r: string) => void;
}) {
  const ranges = mkt.ranges || ['1D'];
  const [internal, setInternal] = useState('1D');
  const range = rangeProp || internal;
  const setRange = onRange || setInternal;
  const r = ranges.includes(range) ? range : ranges[0];
  const gaining = mkt.items.filter((m) => m.byRange[r].chg >= 0).length;
  const status = gaining === mkt.items.length ? 'bullish' : gaining === 0 ? 'bearish' : 'mixed';
  const statusClass = status === 'bullish' ? 'pos' : status === 'bearish' ? 'neg' : 'accent';
  return (
    <div className={`card ${className || ''}`}>
      <CardHead icon="Trending" title="Markets" meta={<span className={`chip ${statusClass}`}>{status}</span>} />
      <div className="range-tabs">
        {ranges.map((rg) => (
          <button key={rg} className={`range-btn ${r === rg ? 'active' : ''}`} onClick={() => setRange(rg)}>{RANGE_LABEL[rg]}</button>
        ))}
      </div>
      <div>
        {mkt.items.map((m) => {
          const d = m.byRange[r];
          const up = d.chg >= 0;
          return (
            <div className="mkt-row" key={m.symbol}>
              <span className="mkt-sym">{m.symbol}</span>
              {expanded && <span className="mkt-name">{m.name}</span>}
              <Spark data={d.spark} color={up ? 'oklch(0.74 0.16 158)' : 'oklch(0.68 0.19 22)'} />
              <span className="mkt-price">${m.price.toLocaleString(undefined, { minimumFractionDigits: m.price < 100 ? 2 : 0, maximumFractionDigits: 2 })}</span>
              <span className={`mkt-chg ${up ? 'up' : 'down'}`}>{up ? '▲' : '▼'}{Math.abs(d.chg)}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function marketSummary(mkt: MarketsVM, r: string) {
  const items = mkt.items;
  const avg = (type: string) => {
    const xs = items.filter((m) => m.type === type);
    return xs.length ? xs.reduce((a, m) => a + m.byRange[r].chg, 0) / xs.length : 0;
  };
  const gaining = items.filter((m) => m.byRange[r].chg >= 0).length;
  const best = items.reduce((a, m) => (m.byRange[r].chg > a.byRange[r].chg ? m : a), items[0]);
  return { gaining, down: items.length - gaining, total: items.length, equities: avg('stock'), crypto: avg('crypto'), best: best.symbol, bestChg: best.byRange[r].chg };
}

export function ScheduleCard({ events, className }: { events: EventVM[]; className?: string }) {
  return (
    <div className={`card ${className || ''}`}>
      <CardHead icon="Calendar" title="Today's Schedule" meta={<span className="chip">{events.length} events</span>} />
      <div className="tl">
        {events.map((e, i) => (
          <div className="tl-item" key={i}>
            <span className="tl-time">{e.start}</span>
            <div className="tl-line">
              <span className={`tl-dot ${e.now ? 'now' : e.past ? 'past' : ''}`}></span>
              <span className="tl-rail"></span>
            </div>
            <div className="tl-body" style={e.past ? { opacity: 0.5 } : undefined}>
              <div className="tl-title">{e.title}{e.now && <span className="tl-now">Now</span>}</div>
              <div className="tl-sub">{e.location}{e.location && ' · '}{e.start}{e.end && `–${e.end}`}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function TasksCard({ tasks, onToggle, className, expanded }: {
  tasks: TaskVM[]; onToggle: (id: string) => void; className?: string; expanded?: boolean;
}) {
  const [filter, setFilter] = useState('all');
  const buckets = ['all', 'work', 'home', 'errands', 'personal'];
  const shown = tasks.filter((t) => filter === 'all' || t.bucket === filter);
  const pending = tasks.filter((t) => !t.done).length;
  const list = expanded ? shown : shown.slice(0, 5);
  return (
    <div className={`card ${className || ''}`}>
      <CardHead icon="CheckSquare" title="Tasks" meta={<span className="chip">{pending} pending</span>} />
      <div className="tabs">
        {buckets.map((b) => (
          <button key={b} className={`tab ${filter === b ? 'active' : ''}`} onClick={() => setFilter(b)}>
            {b === 'all' ? 'All' : b[0].toUpperCase() + b.slice(1)}
          </button>
        ))}
      </div>
      <div>
        {list.map((t) => (
          <div className={`task ${t.done ? 'done' : ''}`} key={t.id}>
            <span className={`prio ${t.priority}`}></span>
            <button className={`check ${t.done ? 'done' : ''}`} onClick={() => onToggle(t.id)} aria-label="toggle"><Icon.Check /></button>
            <span className="task-title">{t.title}</span>
            {t.priority === 'high' && !t.done && <Icon.Alert style={{ width: 14, height: 14, color: 'var(--neg)' }} />}
            <span className="task-tag">{t.bucket}</span>
          </div>
        ))}
        {!expanded && shown.length > 5 && <div className="empty">+{shown.length - 5} more in Tasks →</div>}
        {list.length === 0 && <div className="empty">Nothing here. Nice.</div>}
      </div>
    </div>
  );
}

export function TomorrowCard({ t, className }: { t: TomorrowVM; className?: string }) {
  return (
    <div className={`card ${className || ''}`}>
      <CardHead icon="Sun" title="Tomorrow" meta={<span className="chip">{t.date}</span>} />
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 14 }}>
        <Icon.CloudSun style={{ width: 20, height: 20, color: 'var(--accent-text)' }} />
        <span style={{ fontSize: 13.5, fontWeight: 600 }}>{t.weather.summary}</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-3)' }}>{Math.round(t.weather.temp_hi)}° / {Math.round(t.weather.temp_lo)}°</span>
      </div>
      {t.events.length > 0 && (
        <div className="tl">
          {t.events.map((e, i) => (
            <div className="tl-item" key={i}>
              <span className="tl-time">{e.start}</span>
              <div className="tl-line">
                {/* Tomorrow's events are uniformly future → hollow accent ring. */}
                <span className="tl-dot"></span>
                <span className="tl-rail"></span>
              </div>
              <div className="tl-body">
                <div className="tl-title">{e.title}</div>
                <div className="tl-sub">Leave by {e.leaveBy}{e.commute && ` · ${e.commute}`}</div>
              </div>
            </div>
          ))}
        </div>
      )}
      {t.prep.length > 0 && (
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
          <div className="suggest-label" style={{ marginBottom: 8 }}>Prep tonight</div>
          {t.prep.map((p, i) => (
            <div key={i} style={{ display: 'flex', gap: 9, alignItems: 'center', fontSize: 12.5, color: 'var(--text-2)', padding: '3px 0' }}>
              <span style={{ width: 5, height: 5, borderRadius: 99, background: 'var(--accent)', flexShrink: 0 }}></span>{p}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function CommuteCard({ c, className }: { c: CommuteVM; className?: string }) {
  const driveWins = c.driving.duration <= c.transit.duration;
  return (
    <div className={`card ${className || ''}`}>
      <CardHead icon="Car" title="Commute" meta={<span className="chip">{c.direction}</span>} />
      <div style={{ display: 'flex', gap: 9, alignItems: 'flex-start', padding: '11px 13px', background: 'var(--accent-soft)', borderRadius: 'var(--r-md)', marginBottom: 14 }}>
        <Icon.Sparkle style={{ width: 16, height: 16, color: 'var(--accent-text)', flexShrink: 0, marginTop: 1 }} />
        <span style={{ fontSize: 12.5, color: 'var(--text)', lineHeight: 1.5 }}>{c.recommendation}</span>
      </div>
      <div className="cmt-grid">
        <div className={`cmt-opt ${driveWins ? 'best' : ''}`}>
          <div className="cmt-mode"><Icon.Car /> Driving</div>
          <div className="cmt-dur">{c.driving.duration}<span style={{ fontSize: 13, color: 'var(--text-3)', fontWeight: 500 }}> min</span></div>
          <div className="tl-sub" style={{ marginTop: 6 }}>{c.driving.distance} mi · {c.driving.traffic} traffic</div>
          <div className="tl-sub">{c.driving.route}</div>
        </div>
        <div className={`cmt-opt ${!driveWins ? 'best' : ''}`}>
          <div className="cmt-mode"><Icon.Train /> Transit</div>
          <div className="cmt-dur">{c.transit.duration}<span style={{ fontSize: 13, color: 'var(--text-3)', fontWeight: 500 }}> min</span></div>
          <div className="tl-sub" style={{ marginTop: 6 }}>Caltrain {c.transit.caltrain}m + shuttle {c.transit.shuttle}m</div>
          <div className="tl-sub">Next: {c.transit.next.join(', ')} · #{c.transit.train}</div>
        </div>
      </div>
    </div>
  );
}

export function HabitsCard({ habits, className }: { habits: HabitVM[]; className?: string }) {
  return (
    <div className={`card ${className || ''}`}>
      <CardHead icon="Target" title="Habits" meta={<span className="chip">{habits.filter((h) => h.done).length}/{habits.length} today</span>} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {habits.map((h, i) => (
          <div key={i}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <span style={{ fontSize: 13, fontWeight: 600, flex: 1 }}>{h.name}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--accent-text)', display: 'flex', alignItems: 'center', gap: 3 }}><Icon.Flame style={{ width: 12, height: 12 }} />{h.streak}d</span>
            </div>
            <div style={{ display: 'flex', gap: 5 }}>
              {h.week.map((d, j) => (
                <div key={j} style={{ flex: 1, height: 7, borderRadius: 99, background: d ? 'var(--accent)' : 'var(--surface-2)', border: d ? 'none' : '1px solid var(--border)' }}></div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function NotesCard({ notes, className }: { notes: NoteVM[]; className?: string }) {
  return (
    <div className={`card ${className || ''}`}>
      <CardHead icon="Note" title="Quick Notes" meta={<button className="icon-btn" style={{ width: 26, height: 26 }}><Icon.Plus /></button>} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {notes.map((n, i) => (
          <div key={i} style={{ padding: '10px 12px', background: 'var(--surface-2)', borderRadius: 'var(--r-md)', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: 13, lineHeight: 1.5 }}>{n.text}</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-faint)', marginTop: 6 }}>{n.time}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
