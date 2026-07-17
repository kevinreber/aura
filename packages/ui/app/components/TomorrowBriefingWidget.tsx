import { useState } from 'react';

import type { NaviSuggestion, TomorrowBriefing } from '../lib/api';

interface TomorrowBriefingWidgetProps {
  briefing: TomorrowBriefing | null;
  loading?: boolean;
  error?: string | null;
  collapsed?: boolean;
  onToggle?: () => void;
}

function formatTime(iso: string | null | undefined): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleTimeString([], {
      hour: 'numeric',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

function formatDateHeader(yyyymmdd: string): string {
  // Parse as local-tz date by appending T00:00 — avoids the UTC-midnight
  // shift that bites `new Date('2026-05-18')` (interpreted as UTC).
  try {
    const d = new Date(`${yyyymmdd}T00:00:00`);
    return d.toLocaleDateString([], {
      weekday: 'long',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return yyyymmdd;
  }
}

export function TomorrowBriefingWidget({
  briefing,
  loading = false,
  error = null,
  collapsed = false,
  onToggle,
}: TomorrowBriefingWidgetProps) {
  const eventCount = briefing?.events.length ?? 0;
  const flagCount = briefing?.flags.length ?? 0;

  // Navi's "for your next free window" nudge. Acted-on cards disappear
  // locally; the disposition posts through to Navi's learning loop
  // (best-effort — a failed relay never blocks the UI action).
  const [actedOn, setActedOn] = useState<string[]>([]);
  const naviSection = briefing?.navi_suggestions;
  const naviSuggestions = (naviSection?.suggestions ?? []).filter(
    (s) => !s.id || !actedOn.includes(s.id),
  );
  const sendDisposition = async (s: NaviSuggestion, disposition: string) => {
    if (s.id) setActedOn((ids) => (s.id ? [...ids, s.id] : ids));
    try {
      await fetch('/api/v1/suggestions/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: s.id, disposition }),
      });
    } catch {
      // learning signal lost this once; the card action stands
    }
  };

  return (
    <div
      className={`group rounded-2xl border border-slate-200/70 bg-white/80 shadow-sm shadow-slate-200/40 backdrop-blur-sm transition-all hover:border-slate-300 hover:shadow-md dark:border-white/10 dark:bg-white/[0.04] dark:shadow-none dark:hover:border-white/20 ${collapsed ? 'p-3' : 'p-4 sm:p-6'}`}
    >
      {/* Header */}
      <div className={`flex items-center justify-between ${collapsed ? 'mb-0' : 'mb-4'}`}>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
          🌅 Tomorrow
          {briefing && (
            <span className="ml-2 text-sm font-normal text-gray-600 dark:text-gray-400">
              {formatDateHeader(briefing.date)} · {eventCount} event{eventCount === 1 ? '' : 's'}
              {flagCount > 0 && ` · ${flagCount} flag${flagCount === 1 ? '' : 's'}`}
            </span>
          )}
        </h2>
        {onToggle && (
          <button
            onClick={onToggle}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            aria-label={collapsed ? 'Expand tomorrow briefing' : 'Collapse tomorrow briefing'}
          >
            <svg
              className={`w-4 h-4 text-gray-500 transition-transform ${collapsed ? '' : 'rotate-180'}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        )}
      </div>

      {collapsed ? null : (
        <div className="space-y-4">
          {loading && (
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
              Loading tomorrow's briefing…
            </p>
          )}

          {error && !loading && (
            <p className="text-sm text-red-600 dark:text-red-400">
              Couldn't load tomorrow's briefing: {error}
            </p>
          )}

          {briefing && !loading && (
            <>
              {/* Weather strip */}
              {briefing.weather?.summary && (
                <div className="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-2">
                  <span>🌤️</span>
                  <span>
                    {briefing.weather.summary}
                    {briefing.weather.temp_hi != null && briefing.weather.temp_lo != null && (
                      <> · {briefing.weather.temp_hi}° / {briefing.weather.temp_lo}°</>
                    )}
                    {briefing.weather.precip_chance != null && briefing.weather.precip_chance > 0 && (
                      <> · {briefing.weather.precip_chance}% precip</>
                    )}
                  </span>
                </div>
              )}

              {/* Flags */}
              {briefing.flags.length > 0 && (
                <div className="space-y-1">
                  {briefing.flags.map((flag, i) => (
                    <div
                      key={i}
                      className="text-xs px-3 py-2 rounded-lg bg-amber-50 text-amber-800 dark:bg-amber-900/20 dark:text-amber-200"
                    >
                      ⚠️ {flag}
                    </div>
                  ))}
                </div>
              )}

              {/* Events list */}
              {briefing.events.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                  Nothing on your calendar tomorrow.
                </p>
              ) : (
                <div className="space-y-2">
                  {briefing.events.map((event, i) => {
                    const startTime = event.all_day
                      ? 'All day'
                      : formatTime(event.start_time);
                    return (
                      <div
                        key={event.id ?? `${event.title}-${i}`}
                        className="p-3 rounded-lg bg-gray-50 dark:bg-gray-700/40"
                      >
                        <div className="flex justify-between items-start gap-2">
                          <div className="min-w-0">
                            <div className="font-medium text-sm text-gray-900 dark:text-white truncate">
                              {event.title}
                            </div>
                            {event.location && (
                              <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                📍 {event.location}
                              </div>
                            )}
                          </div>
                          <div className="text-xs text-gray-600 dark:text-gray-300 whitespace-nowrap">
                            {startTime}
                          </div>
                        </div>
                        {event.commute && event.commute.duration_minutes != null && (
                          <div className="mt-2 text-xs text-gray-600 dark:text-gray-300 flex items-center gap-2">
                            <span>🚗</span>
                            <span>
                              {event.commute.leave_by && (
                                <>Leave {formatTime(event.commute.leave_by)} · </>
                              )}
                              {event.commute.duration_minutes} min
                              {event.commute.traffic_status && (
                                <> · {event.commute.traffic_status}</>
                              )}
                            </span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Prep todos */}
              {briefing.prep_todos.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                    Due tomorrow
                  </div>
                  <ul className="space-y-1">
                    {briefing.prep_todos.map((todo) => (
                      <li
                        key={todo.id}
                        className="text-sm text-gray-700 dark:text-gray-300 flex items-start gap-2"
                      >
                        <span className="text-gray-400 mt-0.5">•</span>
                        <span>{todo.title}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Navi suggestions — shown only when Navi said the window is
                  worth it (the worth_notifying gate lives upstream) */}
              {naviSuggestions.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                    For your {naviSection?.window_label ?? 'free window'} · from your saved ideas
                  </div>
                  <div className="space-y-2">
                    {naviSuggestions.map((s, i) => (
                      <div
                        key={s.id ?? `${s.title}-${i}`}
                        className="p-3 rounded-lg bg-emerald-50/70 dark:bg-emerald-900/15"
                      >
                        <div className="flex justify-between items-start gap-2">
                          <div className="min-w-0">
                            <div className="font-medium text-sm text-gray-900 dark:text-white truncate">
                              🧭 {s.title}
                            </div>
                            {(s.rationale || s.location) && (
                              <div className="text-xs text-gray-600 dark:text-gray-300">
                                {s.rationale || s.location}
                              </div>
                            )}
                          </div>
                          {s.url && (
                            <a
                              href={s.url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 whitespace-nowrap"
                            >
                              open ↗
                            </a>
                          )}
                        </div>
                        <div className="mt-2 flex gap-3 text-xs">
                          <button
                            type="button"
                            onClick={() => sendDisposition(s, 'accepted')}
                            className="text-emerald-700 dark:text-emerald-300 hover:underline"
                          >
                            👍 Plan it
                          </button>
                          <button
                            type="button"
                            onClick={() => sendDisposition(s, 'saved')}
                            className="text-gray-600 dark:text-gray-300 hover:underline"
                          >
                            Keep for later
                          </button>
                          <button
                            type="button"
                            onClick={() => sendDisposition(s, 'dismissed')}
                            className="text-gray-500 dark:text-gray-400 hover:underline"
                          >
                            ✕ Not for me
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {briefing.calendar_error && (
                <p className="text-xs text-amber-700 dark:text-amber-300">
                  Calendar fetch issue: {briefing.calendar_error}
                </p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
