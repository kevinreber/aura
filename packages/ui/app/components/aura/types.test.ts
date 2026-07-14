import { describe, expect, it } from 'vitest';
import type { CalendarData } from '../../lib/api';
import { adaptEvents } from './types';

describe('adaptEvents', () => {
  it('falls back to mock events when no data is available (dev/demo)', () => {
    expect(adaptEvents(null).length).toBeGreaterThan(0);
    expect(adaptEvents(undefined).length).toBeGreaterThan(0);
  });

  it('returns an empty list — not mock events — when the payload carries an error', () => {
    const errored: CalendarData = {
      tool: 'calendar',
      data: {
        events: [],
        total_events: 0,
        error: 'Google Calendar authentication expired — re-authentication required',
        auth_expired: true,
      },
      timestamp: new Date().toISOString(),
    };
    expect(adaptEvents(errored)).toEqual([]);
  });

  it('maps real events through unchanged', () => {
    const data: CalendarData = {
      tool: 'calendar',
      data: {
        events: [
          {
            title: 'Standup',
            start_time: '2026-07-14T09:00:00',
            end_time: '2026-07-14T09:15:00',
          },
        ],
        total_events: 1,
      },
      timestamp: new Date().toISOString(),
    };
    const vm = adaptEvents(data);
    expect(vm).toHaveLength(1);
    expect(vm[0].title).toBe('Standup');
  });
});
