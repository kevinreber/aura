// View-model types for the Aura UI components + adapters from the live
// `~/lib/api` response shapes. Each adapter accepts the (possibly null)
// server data and falls back to mock values so the UI always renders.
import type {
  WeatherData,
  FinancialData,
  CalendarData,
  TodoData,
  CommuteOptionsData,
  TomorrowBriefing,
} from '../../lib/api';

/* ---------- view-model shapes ---------- */
export interface WeatherVM {
  location: string;
  current_temp: number;
  condition: string;
  temp_hi: number;
  temp_lo: number;
  precip_chance: number;
  humidity: number;
  wind: number;
}
export interface MarketItem {
  symbol: string;
  name: string;
  price: number;
  type: 'stock' | 'crypto';
  byRange: Record<string, { chg: number; spark: number[] }>;
}
export interface MarketsVM { ranges: string[]; items: MarketItem[]; }
export interface EventVM { title: string; start: string; end: string; cat: string; location: string; past?: boolean; now?: boolean; }
export interface TaskVM { id: string; title: string; bucket: string; priority: string; done: boolean; }
export interface TomorrowVM {
  date: string;
  weather: { summary: string; temp_hi: number; temp_lo: number; precip_chance: number };
  events: { title: string; start: string; leaveBy: string; commute: string }[];
  prep: string[];
}
export interface CommuteVM {
  direction: string;
  recommendation: string;
  driving: { duration: number; distance: number; traffic: string; fuel: number; route: string };
  transit: { duration: number; caltrain: number; shuttle: number; walk: number; next: string[]; train: string };
}
export interface HabitVM { name: string; streak: number; done: boolean; target: number; week: number[]; }
export interface NoteVM { text: string; time: string; }
export interface ChatMsg { type: 'user' | 'ai'; message: string; timestamp: string; }

/* ---------- helpers ---------- */
// Deterministic sparkline from start→end with mild jitter (shape only).
export function genSpark(start: number, end: number, n: number, seed = 1): number[] {
  let s = seed;
  const rnd = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
  const out: number[] = [];
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    out.push(+(start + (end - start) * t + (rnd() - 0.5) * Math.abs(end - start || 1) * 0.5).toFixed(3));
  }
  out[0] = start; out[n - 1] = end;
  return out;
}

function fmtTime(iso?: string): string {
  if (!iso) return '';
  const d = new Date(iso.includes('T') ? iso : iso.replace(' ', 'T'));
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

/* ---------- adapters ---------- */
export function adaptWeather(w: WeatherData | null | undefined): WeatherVM {
  const d = w?.data;
  return {
    location: d?.location ?? 'San Francisco, US',
    current_temp: d?.current_temp ?? 67,
    condition: d?.condition ?? 'Few Clouds',
    temp_hi: d?.temp_hi ?? 68,
    temp_lo: d?.temp_lo ?? 52,
    precip_chance: d?.precip_chance ?? 8,
    // humidity/wind aren't in the current API payload — surfaced as 0 if absent.
    humidity: (d as { humidity?: number })?.humidity ?? 0,
    wind: (d as { wind?: number })?.wind ?? 0,
  };
}

const RANGES = ['1D', '1W', '30D', '90D', '1Y'];
const N_PTS: Record<string, number> = { '1D': 8, '1W': 8, '30D': 10, '90D': 12, '1Y': 14 };
// Multipliers to synthesize longer-range % from the live 1D change until the
// API returns real historical series. Replace `byRange` with real data then.
const RANGE_MULT: Record<string, number> = { '1D': 1, '1W': 1.8, '30D': 3.4, '90D': 6.1, '1Y': 9.5 };

export function adaptMarkets(f: FinancialData | null | undefined): MarketsVM {
  const rows = f?.data?.data ?? [
    { symbol: 'MSFT', name: 'Microsoft', price: 450.24, change_percent: 5.4, data_type: 'stocks' },
    { symbol: 'NVDA', name: 'NVIDIA', price: 875.12, change_percent: 2.1, data_type: 'stocks' },
    { symbol: 'BTC', name: 'Bitcoin', price: 73514, change_percent: -0.6, data_type: 'crypto' },
    { symbol: 'ETH', name: 'Ethereum', price: 1997, change_percent: -1.3, data_type: 'crypto' },
  ];
  let seed = 7;
  const items: MarketItem[] = rows.map((r, idx) => {
    const byRange: MarketItem['byRange'] = {};
    RANGES.forEach((rg) => {
      const chg = +(r.change_percent * RANGE_MULT[rg]).toFixed(1);
      byRange[rg] = { chg, spark: genSpark(10, 10 + chg / 4, N_PTS[rg], (seed += 17 + idx * 5)) };
    });
    return { symbol: r.symbol, name: r.name, price: r.price, type: r.data_type === 'crypto' ? 'crypto' : 'stock', byRange };
  });
  return { ranges: RANGES, items };
}

// Build a local-time Date for "today at h:m". Used by the mock-event
// fallback so past/now flags reflect the real wall clock rather than
// shipping hardcoded values that go stale by mid-morning.
function todayAt(h: number, m = 0): number {
  const d = new Date();
  d.setHours(h, m, 0, 0);
  return d.getTime();
}

function classify(startMs: number, endMs: number, now: number) {
  return {
    past: !Number.isNaN(endMs) && endMs < now,
    now: !Number.isNaN(startMs) && startMs <= now && (Number.isNaN(endMs) || endMs >= now),
  };
}

export function adaptEvents(c: CalendarData | null | undefined): EventVM[] {
  const events = c?.data?.events;
  const now = Date.now();
  if (!events?.length) {
    return [
      { title: 'Team Standup', start: '9:00 AM', end: '9:15 AM', cat: 'work', location: 'Zoom',
        ...classify(todayAt(9), todayAt(9, 15), now) },
      { title: 'Code Review', start: '2:00 PM', end: '3:00 PM', cat: 'work', location: 'PR #16',
        ...classify(todayAt(14), todayAt(15), now) },
      { title: 'Gym Session', start: '6:00 PM', end: '7:00 PM', cat: 'personal', location: 'Mission Cliffs',
        ...classify(todayAt(18), todayAt(19), now) },
    ];
  }
  return events.map((e) => {
    const startMs = new Date((e.start_time || '').replace(' ', 'T')).getTime();
    const endMs = new Date((e.end_time || '').replace(' ', 'T')).getTime();
    return {
      title: e.title,
      start: e.all_day ? 'All day' : fmtTime(e.start_time),
      end: fmtTime(e.end_time),
      cat: e.calendar_source || 'work',
      location: e.location || '',
      ...classify(startMs, endMs, now),
    };
  });
}

export function adaptTodos(t: TodoData | null | undefined, completions: Record<string, boolean> = {}): TaskVM[] {
  const items = t?.data?.items;
  if (!items?.length) {
    return [
      { id: '1', title: 'Prepare for client presentation', bucket: 'work', priority: 'high', done: false },
      { id: '2', title: 'Update project documentation', bucket: 'work', priority: 'medium', done: false },
      { id: '3', title: 'Plan sprint retrospective', bucket: 'work', priority: 'medium', done: false },
      { id: '4', title: 'Grocery shopping', bucket: 'home', priority: 'medium', done: false },
      { id: '5', title: 'Pick up dry cleaning', bucket: 'errands', priority: 'low', done: false },
      { id: '6', title: 'Call insurance company', bucket: 'personal', priority: 'low', done: false },
    ];
  }
  return items.map((i) => ({
    id: i.id,
    title: i.title,
    bucket: i.bucket || 'work',
    priority: i.priority || 'low',
    done: completions[i.id] ?? i.completed,
  }));
}

export function adaptTomorrow(t: TomorrowBriefing | null | undefined): TomorrowVM {
  if (!t) {
    return {
      date: 'Tomorrow',
      weather: { summary: 'Clear Sky', temp_hi: 67, temp_lo: 52, precip_chance: 4 },
      events: [{ title: 'Daily Standup', start: '9:30 AM', leaveBy: '9:10 AM', commute: '14 min drive' }],
      prep: ['Prep slides for client presentation'],
    };
  }
  return {
    date: new Date(t.date).toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' }),
    weather: {
      summary: t.weather?.summary ?? '—',
      temp_hi: t.weather?.temp_hi ?? 0,
      temp_lo: t.weather?.temp_lo ?? 0,
      precip_chance: t.weather?.precip_chance ?? 0,
    },
    events: (t.events ?? []).map((e) => ({
      title: e.title,
      start: fmtTime(e.start_time),
      leaveBy: e.commute?.leave_by ? fmtTime(e.commute.leave_by) : '—',
      commute: e.commute?.duration_minutes != null ? `${e.commute.duration_minutes} min` : '',
    })),
    prep: (t.prep_todos ?? []).map((p) => p.title),
  };
}

export function adaptCommute(c: CommuteOptionsData | null | undefined): CommuteVM {
  const d = c?.data;
  return {
    direction: d?.direction === 'from_work' ? 'To Home' : 'To Work',
    recommendation: d?.recommendation ?? 'Driving and transit are close today.',
    driving: {
      duration: d?.driving?.duration_minutes ?? 38,
      distance: d?.driving?.distance_miles ?? 28.5,
      traffic: d?.driving?.traffic_status ?? 'Moderate',
      fuel: d?.driving?.estimated_fuel_gallons ?? 1.1,
      route: d?.driving?.route_summary ?? 'US-101 S → I-880 S',
    },
    transit: (() => {
      // `[].map() || fallback` doesn't fire — empty arrays are truthy. Check
      // length explicitly so we fall back when the transit feed returns no
      // departures (UI shows two placeholder times instead of an empty card).
      const nextRaw = (d?.transit?.next_departures ?? []).slice(0, 2).map((n) => n.departure_time);
      return {
        duration: d?.transit?.total_duration_minutes ?? 63,
        caltrain: d?.transit?.caltrain_duration_minutes ?? 47,
        shuttle: d?.transit?.shuttle_duration_minutes ?? 11,
        walk: d?.transit?.walking_duration_minutes ?? 3,
        next: nextRaw.length ? nextRaw : ['8:15 AM', '8:45 AM'],
        train: d?.transit?.next_departures?.[0]?.train_number ?? '152',
      };
    })(),
  };
}

/* ---------- UI-only mock data (no API source yet) ---------- */
export const MOCK_HABITS: HabitVM[] = [
  { name: 'Morning workout', streak: 12, done: true, target: 5, week: [1, 1, 0, 1, 1, 0, 1] },
  { name: 'Read 20 minutes', streak: 7, done: true, target: 7, week: [1, 1, 1, 1, 1, 1, 1] },
  { name: 'No phone after 10pm', streak: 3, done: false, target: 5, week: [1, 0, 1, 1, 0, 0, 0] },
];
export const MOCK_NOTES: NoteVM[] = [
  { text: 'Ask design about the new onboarding flow before Thursday', time: '11:02 AM' },
  { text: 'Idea: weekly digest email summarizing Aura activity', time: 'Yesterday' },
];
export const WEEKEND_CATS = [
  { cat: 'Trails & Outdoors', icon: 'Mountain', desc: 'Hiking, running, and cycling near you', prompts: ['Find hiking trails near my area', "What's a good easy trail under 5 miles?", 'Suggest a moderate hike for this weekend'] },
  { cat: 'Live Music', icon: 'Music', desc: 'Upcoming concerts and live events', prompts: ['What concerts are happening this weekend?', 'Any live music in the next two weeks?', 'Find concerts for my favorite artists'] },
  { cat: 'Multi-day Trips', icon: 'Map', desc: 'Full weekend trips with points of interest', prompts: ['Plan a 2-day trip with food and outdoors', 'Suggest a weekend itinerary near me', 'A long weekend within 4 hours of me?'] },
] as const;
