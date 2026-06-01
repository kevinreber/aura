// Aura desktop shell — three panes (rail · views · copilot). Fully
// presentational: the container passes data + callbacks. Manages only local
// view/range/timer UI state.
import { useEffect, useRef, useState } from 'react';
import { Icon, type IconName } from './icons';
import {
  WeatherCard, MarketsCard, ScheduleCard, TasksCard, TomorrowCard,
  CommuteCard, HabitsCard, NotesCard, CardHead, marketSummary,
  ScheduleTabsCard,
} from './widgets';
import { Copilot } from './Copilot';
import { WEEKEND_CATS } from './types';
import type {
  WeatherVM, MarketsVM, EventVM, TaskVM, TomorrowVM, CommuteVM, HabitVM, NoteVM, ChatMsg,
} from './types';

export interface AuraShellProps {
  userName: string;
  userEmail?: string;
  weather: WeatherVM;
  markets: MarketsVM;
  events: EventVM[];
  tasks: TaskVM[];
  tomorrow: TomorrowVM;
  commute: CommuteVM;
  habits: HabitVM[];
  notes: NoteVM[];
  onToggleTodo: (id: string) => void;
  // chat
  messages: ChatMsg[];
  streaming?: string;
  isLoadingChat?: boolean;
  onSend: (text: string) => void;
  onClearChat?: () => void;
  // chrome
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
  onSignOut?: () => void;
}

type View = 'today' | 'calendar' | 'tasks' | 'markets' | 'commute' | 'weekend' | 'focus';

const SUGGESTIONS: Record<View, string[]> = {
  today: ['What should I focus on first?', 'Summarize my day', 'Move my 2pm if it rains'],
  tasks: ['Group my tasks by effort', "What's overdue?", 'Draft my sprint retro agenda'],
  markets: ['Why is MSFT up today?', 'Summarize my watchlist', 'Set an alert for BTC under 70k'],
  commute: ['Best time to leave for work?', 'Is transit faster tomorrow?', 'Avoid the bridge today'],
  weekend: ['Plan a 2-day trip near me', 'Easy hike under 5 miles?', 'Concerts this weekend'],
  focus: ['Start a 25-min focus block', "What's my longest habit streak?", 'Add a note for later'],
  calendar: ['What\u2019s my next meeting?', 'Find a free hour today', 'Block focus time at 4pm'],
};

function greeting(h: number) { return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'; }

function LiveClock({ theme, onToggleTheme }: { theme: 'dark' | 'light'; onToggleTheme: () => void }) {
  const [now, setNow] = useState(new Date());
  useEffect(() => { const t = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(t); }, []);
  return (
    <div className="clock-card" style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
      <div style={{ textAlign: 'right' }}>
        <div className="clock-time">{now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true })}</div>
        <div className="clock-date">{now.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}</div>
      </div>
      <button className="icon-btn" onClick={onToggleTheme} title="Toggle theme">
        {theme === 'dark' ? <Icon.Sun /> : <Icon.Moon />}
      </button>
    </div>
  );
}

function ViewHeader({ eyebrow, title, sub }: { eyebrow: string; title: string; sub: string }) {
  return (
    <div className="main-head fade-in">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1 className="greeting" style={{ fontSize: 28 }}>{title}</h1>
        <p className="sub">{sub}</p>
      </div>
    </div>
  );
}

function FocusTimer() {
  const [secs, setSecs] = useState(25 * 60);
  const [running, setRunning] = useState(false);
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setSecs((s) => (s <= 1 ? (setRunning(false), 25 * 60) : s - 1)), 1000);
    return () => clearInterval(t);
  }, [running]);
  const mm = String(Math.floor(secs / 60)).padStart(2, '0');
  const ss = String(secs % 60).padStart(2, '0');
  const pct = ((25 * 60 - secs) / (25 * 60)) * 100;
  return (
    <div className="card span-2" style={{ alignItems: 'center', textAlign: 'center', justifyContent: 'center', padding: '28px 18px' }}>
      <div className="card-ic" style={{ marginBottom: 14 }}><Icon.Timer /></div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 54, fontWeight: 500, letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums' }}>{mm}:{ss}</div>
      <div style={{ height: 6, width: '100%', borderRadius: 99, background: 'var(--surface-2)', overflow: 'hidden', margin: '16px 0 18px' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: 'var(--accent)', borderRadius: 99 }}></div>
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <button className="tab active" style={{ padding: '8px 20px' }} onClick={() => setRunning((r) => !r)}>{running ? 'Pause' : 'Start'}</button>
        <button className="tab" style={{ padding: '8px 16px' }} onClick={() => { setRunning(false); setSecs(25 * 60); }}>Reset</button>
      </div>
    </div>
  );
}

const NAV: { id: View; label: string; icon: IconName; count?: number }[] = [
  { id: 'today', label: 'Today', icon: 'Home' },
  { id: 'calendar', label: 'Calendar', icon: 'Calendar' },
  { id: 'tasks', label: 'Tasks', icon: 'CheckSquare' },
  { id: 'markets', label: 'Markets', icon: 'Trending' },
  { id: 'commute', label: 'Commute', icon: 'Car' },
];
const NAV2: { id: View; label: string; icon: IconName }[] = [
  { id: 'weekend', label: 'Weekend', icon: 'Mountain' },
  { id: 'focus', label: 'Focus', icon: 'Target' },
];

export function AuraShell(props: AuraShellProps) {
  const { userName, weather, markets, events, tasks, tomorrow, commute, habits, notes, onToggleTodo } = props;
  const [view, setView] = useState<View>('today');
  const [range, setRange] = useState('1D');
  const [sheetOpen, setSheetOpen] = useState(false); // mobile copilot sheet
  const mainRef = useRef<HTMLDivElement>(null);
  useEffect(() => { if (mainRef.current) mainRef.current.scrollTop = 0; }, [view]);
  const goTo = (v: View) => { setView(v); setSheetOpen(false); };

  const pending = tasks.filter((t) => !t.done).length;
  const fmtPct = (n: number) => `${n >= 0 ? '+' : '−'}${Math.abs(n).toFixed(1)}%`;
  const rangeWord: Record<string, string> = { '1D': 'today', '1W': 'this week', '30D': 'in 30 days', '90D': 'in 90 days', '1Y': 'this year' };
  const now = new Date();

  // Per-view eyebrow + title rendered in the mobile sticky topbar's hero.
  const viewHead: { eyebrow: string; title: React.ReactNode } = (() => {
    switch (view) {
      case 'today':
        return {
          eyebrow: now.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' }),
          title: (<>{greeting(now.getHours())}, {userName}.<span className="dim"> Here's your day.</span></>),
        };
      case 'tasks': return { eyebrow: 'Tasks', title: 'Everything on your list' };
      case 'markets': return { eyebrow: 'Markets', title: 'Your watchlist' };
      case 'calendar': return { eyebrow: 'Calendar', title: "Today's schedule" };
      case 'commute': return { eyebrow: 'Commute', title: 'Getting to work' };
      case 'weekend': return { eyebrow: 'Weekend', title: 'Plan your weekend' };
      case 'focus': return { eyebrow: 'Focus', title: 'Deep work' };
    }
  })();

  const NavBtn = ({ item }: { item: { id: View; label: string; icon: IconName; count?: number } }) => {
    const Ic = Icon[item.icon];
    return (
      <button className={`nav-item ${view === item.id ? 'active' : ''}`} onClick={() => goTo(item.id)}>
        <Ic /><span className="label">{item.label}</span>
        {item.count != null && <span className="count">{item.count}</span>}
      </button>
    );
  };

  const s = marketSummary(markets, range);

  return (
    <div className="shell">
      {/* LEFT RAIL */}
      <nav className="rail">
        <div className="brand">
          <div className="brand-mark"><Icon.Sparkle style={{ width: 18, height: 18, color: '#fff' }} /></div>
          <div><div className="brand-name">Aura</div><div className="brand-sub">Daily Agent</div></div>
        </div>
        <div className="nav-label">Briefing</div>
        {NAV.map((n) => <NavBtn item={{ ...n, count: n.id === 'tasks' ? pending : n.id === 'calendar' ? events.length : undefined }} key={n.id} />)}
        <div className="nav-label">Explore</div>
        {NAV2.map((n) => <NavBtn item={n} key={n.id} />)}

        <div className="rail-foot">
          <div className="agent-status">
            <span className="status-dot status-pulse"></span>
            <div className="meta" style={{ lineHeight: 1.3 }}>
              <div style={{ fontSize: 12, fontWeight: 600 }}>All systems live</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-3)' }}>6 tools connected</div>
            </div>
          </div>
          <div className="user-row" onClick={props.onSignOut}>
            <div className="avatar" style={{ display: 'grid', placeItems: 'center', background: 'linear-gradient(145deg, var(--accent), oklch(0.62 0.2 320))', color: '#fff', fontSize: 13, fontWeight: 700 }}>{userName[0]}</div>
            <div className="meta" style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12.5, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{userName}</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-3)' }}>Sign out</div>
            </div>
            <Icon.LogOut style={{ width: 15, height: 15, color: 'var(--text-3)' }} className="meta" />
          </div>
        </div>
      </nav>

      {/* CENTER */}
      <main className="main scroll" ref={mainRef}>
        {/* Mobile-only sticky header (≤860px) — desktop uses the rail brand
            + LiveClock instead. Always full-height so the eyebrow, greeting,
            and (Today-only) KPIs stay visible while content scrolls beneath. */}
        <header className="shell-topbar">
          <div className="shell-topbar-bar">
            <div className="brand">
              <div className="brand-mark"><Icon.Sparkle style={{ width: 18, height: 18, color: '#fff' }} /></div>
              <div>
                <div className="brand-name">Aura</div>
                <div className="brand-sub">Daily Agent</div>
              </div>
            </div>
            <button className="icon-btn" onClick={props.onToggleTheme} title="Toggle theme" aria-label="Toggle theme">
              {props.theme === 'dark' ? <Icon.Sun /> : <Icon.Moon />}
            </button>
          </div>
          <div className="shell-topbar-hero">
            <div className="eyebrow">{viewHead.eyebrow}</div>
            <h1 className="greeting">{viewHead.title}</h1>
          </div>
          {view === 'today' && (
            <div className="shell-topbar-kpis">
              <div className="kpi"><span className="k"><Icon.Calendar /> Events</span><span className="v">{events.length}</span></div>
              <div className="kpi"><span className="k"><Icon.CheckSquare /> Pending</span><span className="v">{pending}</span></div>
              <div className="kpi"><span className="k"><Icon.CloudSun /> Now</span><span className="v">{Math.round(weather.current_temp)}°</span></div>
            </div>
          )}
        </header>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 4 }}>
          <LiveClock theme={props.theme} onToggleTheme={props.onToggleTheme} />
        </div>

        {view === 'today' && (
          <>
            <div className="main-head">
              <div className="fade-in">
                <div className="eyebrow">{now.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' })}</div>
                <h1 className="greeting">{greeting(now.getHours())}, {userName}.<span className="dim"> Here's your day.</span></h1>
                <p className="sub">Everything that matters today — schedule, tasks, markets, and weather, in one view. Aura is standing by on the right.</p>
              </div>
              <div className="kpi-row" style={{ maxWidth: 360 }}>
                <div className="kpi"><span className="k"><Icon.Calendar /> Events</span><span className="v">{events.length}</span></div>
                <div className="kpi"><span className="k"><Icon.CheckSquare /> Pending</span><span className="v">{pending}</span></div>
                <div className="kpi"><span className="k"><Icon.CloudSun /> Now</span><span className="v">{Math.round(weather.current_temp)}°</span></div>
              </div>
            </div>
            {/* Desktop layout — standard bento sections. */}
            <div className="only-desktop">
              <div className="section-title">At a glance</div>
              <div className="bento">
                <ScheduleCard events={events} className="span-3" />
                <div className="span-3" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <WeatherCard wx={weather} />
                  <MarketsCard mkt={markets} />
                </div>
              </div>
              <div className="section-title">On your plate</div>
              <div className="bento">
                <TasksCard tasks={tasks} onToggle={onToggleTodo} className="span-4" />
                <TomorrowCard t={tomorrow} className="span-2" />
              </div>
              <div className="section-title">Looking ahead</div>
              <div className="bento">
                <CommuteCard c={commute} className="span-3" />
                <HabitsCard habits={habits} className="span-3" />
              </div>
            </div>

            {/* Mobile layout — reordered for phone IA:
                  At a glance → tabbed Schedule + Commute (what's next + how to get there)
                  On your plate → Tasks
                  Looking ahead → Weather (compact), Markets, Habits */}
            <div className="only-mobile">
              <div className="section-title">At a glance</div>
              <div className="bento">
                <ScheduleTabsCard events={events} tomorrow={tomorrow} className="span-6" />
                <CommuteCard c={commute} className="span-6" />
              </div>
              <div className="section-title">On your plate</div>
              <div className="bento">
                <TasksCard tasks={tasks} onToggle={onToggleTodo} className="span-6" />
              </div>
              <div className="section-title">Looking ahead</div>
              <div className="bento">
                <WeatherCard wx={weather} className="span-6" />
                <MarketsCard mkt={markets} className="span-6" />
                <HabitsCard habits={habits} className="span-6" />
              </div>
            </div>
          </>
        )}

        {view === 'tasks' && (
          <>
            <ViewHeader eyebrow="Tasks" title="Everything on your list" sub={`${pending} open · ${tasks.length - pending} completed across work, home, errands, and personal.`} />
            <div className="bento">
              <TasksCard tasks={tasks} onToggle={onToggleTodo} className="span-4" expanded />
              <div className="span-2" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div className="card">
                  <CardHead icon="Target" title="Progress" />
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                    {['work', 'home', 'errands', 'personal'].map((b) => {
                      const all = tasks.filter((t) => t.bucket === b);
                      const dn = all.filter((t) => t.done).length;
                      const pct = all.length ? Math.round((dn / all.length) * 100) : 0;
                      return (
                        <div key={b}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, marginBottom: 6 }}>
                            <span style={{ textTransform: 'capitalize', fontWeight: 600 }}>{b}</span>
                            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-3)' }}>{dn}/{all.length}</span>
                          </div>
                          <div style={{ height: 7, borderRadius: 99, background: 'var(--surface-2)', overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${pct}%`, background: 'var(--accent)', borderRadius: 99 }}></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
                <NotesCard notes={notes} />
              </div>
            </div>
          </>
        )}

        {view === 'markets' && (
          <>
            <ViewHeader eyebrow="Markets" title="Your watchlist" sub="Live quotes across equities and crypto. Pick a range to see how each has moved." />
            <div className="bento">
              <MarketsCard mkt={markets} className="span-4" expanded range={range} onRange={setRange} />
              <div className="card span-2">
                <CardHead icon="Wallet" title="Summary" meta={<span className="chip accent">{range}</span>} />
                <div style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.6 }}>
                  <strong style={{ color: 'var(--text)' }}>{s.total} instruments</strong> tracked · <span className="up">{s.gaining} gaining</span>, <span className="down">{s.down} down</span>. Best mover {rangeWord[range]} is <strong style={{ color: 'var(--text)' }}>{s.best} ({fmtPct(s.bestChg)})</strong>.
                </div>
                <div style={{ marginTop: 16, display: 'flex', gap: 10 }}>
                  <div className="kpi"><span className="k">Equities</span><span className={`v ${s.equities >= 0 ? 'up' : 'down'}`}>{fmtPct(s.equities)}</span></div>
                  <div className="kpi"><span className="k">Crypto</span><span className={`v ${s.crypto >= 0 ? 'up' : 'down'}`}>{fmtPct(s.crypto)}</span></div>
                </div>
              </div>
            </div>
          </>
        )}

        {view === 'calendar' && (
          <>
            <ViewHeader eyebrow="Calendar" title="Today's schedule" sub={`${events.length} events on your calendar. Tomorrow: ${tomorrow.events.length} event(s).`} />
            <div className="bento">
              <ScheduleTabsCard events={events} tomorrow={tomorrow} className="span-6 only-mobile" />
              <ScheduleCard events={events} className="span-3 only-desktop" />
              <TomorrowCard t={tomorrow} className="span-3 only-desktop" />
            </div>
          </>
        )}

        {view === 'commute' && (
          <>
            <ViewHeader eyebrow="Commute" title="Getting to work" sub="Real-time driving and transit options with a recommendation." />
            <div className="bento">
              <CommuteCard c={commute} className="span-4" />
              <div className="card span-2">
                <CardHead icon="Clock" title="Departures" />
                <div className="suggest-label">Next Caltrain</div>
                {commute.transit.next.map((t, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '9px 0', borderTop: i ? '1px solid var(--border)' : 'none', fontFamily: 'var(--font-mono)', fontSize: 13, whiteSpace: 'nowrap' }}>
                    <span>{t}</span><span style={{ color: 'var(--text-3)' }}>#{commute.transit.train}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {view === 'weekend' && (
          <>
            <ViewHeader eyebrow="Weekend" title="Plan your weekend" sub="Ideas powered by your interests. Tap any prompt to send it to Aura." />
            <div className="bento">
              <div className="card span-6">
                <CardHead icon="Sparkle" title="Weekend Planner" meta={<span className="chip">3 categories</span>} />
                <div className="weekend-grid">
                  {WEEKEND_CATS.map((cat, i) => {
                    const CatIcon = Icon[cat.icon as IconName];
                    return (
                      <div className="prompt-cat" key={i}>
                        <div className="prompt-cat-head">
                          <div className="card-ic"><CatIcon /></div>
                          <div><div style={{ fontSize: 13, fontWeight: 600 }}>{cat.cat}</div><div className="tl-sub">{cat.desc}</div></div>
                        </div>
                        <div className="prompt-list">
                          {cat.prompts.map((p, j) => (
                            <button className="prompt-pill" key={j} onClick={() => props.onSend(p)}>{p}<Icon.Arrow /></button>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </>
        )}

        {view === 'focus' && (
          <>
            <ViewHeader eyebrow="Focus" title="Deep work" sub="A Pomodoro timer, your habits, and a scratchpad for thoughts." />
            <div className="bento">
              <FocusTimer />
              <HabitsCard habits={habits} className="span-2" />
              <NotesCard notes={notes} className="span-2" />
            </div>
          </>
        )}
      </main>

      {/* RIGHT RAIL (desktop) / SLIDE-UP SHEET (mobile) */}
      <Copilot
        messages={props.messages}
        streaming={props.streaming}
        isLoading={props.isLoadingChat}
        suggestions={SUGGESTIONS[view]}
        onSend={props.onSend}
        onClear={props.onClearChat}
        sheetOpen={sheetOpen}
        onCloseSheet={() => setSheetOpen(false)}
      />

      {/* MOBILE-ONLY chrome (hidden ≥860px via CSS) */}
      <button className="shell-fab" onClick={() => setSheetOpen(true)} aria-label="Ask Aura">
        <Icon.Sparkle /><span className="fab-dot"></span>
      </button>
      <nav className="shell-tabbar">
        {([...NAV, ...NAV2] as { id: View; label: string; icon: IconName }[]).filter((n) => ['today', 'tasks', 'markets', 'weekend', 'focus'].includes(n.id)).map((n) => {
          const Ic = Icon[n.icon];
          return (
            <button key={n.id} className={`m-tab ${view === n.id ? 'active' : ''}`} onClick={() => goTo(n.id)}>
              <Ic /><span>{n.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
