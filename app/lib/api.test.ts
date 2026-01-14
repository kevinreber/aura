import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { AIAgentAPI } from './api';

describe('AIAgentAPI', () => {
  let api: AIAgentAPI;

  beforeEach(() => {
    api = new AIAgentAPI();
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe('getWeather', () => {
    it('returns weather data on successful fetch', async () => {
      const mockWeather = {
        tool: 'weather',
        data: {
          location: 'San Francisco',
          current_temp: 72,
          condition: 'Sunny',
          temp_hi: 78,
          temp_lo: 65,
          precip_chance: 5,
          summary: 'Clear and sunny',
        },
        timestamp: '2024-06-15T10:00:00Z',
      };

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockWeather),
      } as Response);

      const result = await api.getWeather('San Francisco');

      expect(result).toEqual(mockWeather);
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/tools/weather?'),
        expect.objectContaining({
          headers: { 'Content-Type': 'application/json' },
        })
      );
    });

    it('returns mock data on fetch failure', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('Network error'));

      const result = await api.getWeather();

      expect(result.tool).toBe('weather');
      expect(result.data.location).toBe('San Francisco');
      expect(result.data.current_temp).toBeDefined();
    });
  });

  describe('getFinancialData', () => {
    it('posts with correct symbols', async () => {
      const mockFinancial = {
        tool: 'financial',
        data: {
          summary: 'Market summary',
          total_items: 4,
          market_status: 'open',
          data: [],
        },
        timestamp: '2024-06-15T10:00:00Z',
      };

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockFinancial),
      } as Response);

      const symbols = ['AAPL', 'GOOGL'];
      await api.getFinancialData(symbols);

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/tools/financial'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            symbols,
            data_type: 'mixed',
          }),
        })
      );
    });

    it('returns mock data on fetch failure', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('Network error'));

      const result = await api.getFinancialData();

      expect(result.tool).toBe('financial');
      expect(result.data.data.length).toBeGreaterThan(0);
    });
  });

  describe('getCalendar', () => {
    it('fetches calendar with optional date parameter', async () => {
      const mockCalendar = {
        tool: 'calendar',
        data: { events: [], total_events: 0 },
        timestamp: '2024-06-15T10:00:00Z',
      };

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCalendar),
      } as Response);

      await api.getCalendar('2024-06-15');

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('date=2024-06-15'),
        expect.anything()
      );
    });

    it('returns mock data on failure', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('Network error'));

      const result = await api.getCalendar();

      expect(result.tool).toBe('calendar');
      expect(result.data.events).toBeInstanceOf(Array);
    });
  });

  describe('getTodos', () => {
    it('fetches all todos without bucket filter', async () => {
      const mockTodos = {
        tool: 'todos',
        data: { items: [], total_pending: 0 },
        timestamp: '2024-06-15T10:00:00Z',
      };

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockTodos),
      } as Response);

      await api.getTodos();

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/tools/todos'),
        expect.anything()
      );
    });

    it('fetches todos with bucket filter', async () => {
      const mockTodos = {
        tool: 'todos',
        data: { items: [], total_pending: 0, bucket: 'work' },
        timestamp: '2024-06-15T10:00:00Z',
      };

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockTodos),
      } as Response);

      await api.getTodos('work');

      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('bucket=work'), expect.anything());
    });

    it('returns filtered mock data on failure', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('Network error'));

      const result = await api.getTodos('work');

      expect(result.tool).toBe('todos');
      // Mock todos should be filtered by bucket
      expect(result.data.bucket).toBe('work');
    });
  });

  describe('sendChatMessage', () => {
    it('sends message and returns response', async () => {
      const mockResponse = {
        response: 'Hello! How can I help you?',
        timestamp: '2024-06-15T10:00:00Z',
      };

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      } as Response);

      const result = await api.sendChatMessage('Hello');

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/chat'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ message: 'Hello' }),
        })
      );
      expect(result.response).toBe('Hello! How can I help you?');
    });

    it('throws error on failure (no fallback)', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('Network error'));

      await expect(api.sendChatMessage('Hello')).rejects.toThrow('Network error');
    });
  });

  describe('getCommuteOptions', () => {
    it('sends commute request with correct parameters', async () => {
      const mockCommute = {
        tool: 'commute_options',
        data: {
          direction: 'to_work',
          query_time: '2024-06-15T08:00:00Z',
          recommendation: 'Take the train',
        },
        timestamp: '2024-06-15T10:00:00Z',
      };

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCommute),
      } as Response);

      await api.getCommuteOptions('to_work', '08:00', true, false);

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/tools/commute-options'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            direction: 'to_work',
            include_driving: true,
            include_transit: false,
            departure_time: '08:00',
          }),
        })
      );
    });

    it('returns mock data on failure', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('Network error'));

      const result = await api.getCommuteOptions('to_work');

      expect(result.tool).toBe('commute_options');
      expect(result.data.direction).toBe('to_work');
    });
  });

  describe('API error handling', () => {
    it('handles non-ok response', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      } as Response);

      // sendChatMessage throws on error
      await expect(api.sendChatMessage('test')).rejects.toThrow('API Error: 500');
    });
  });
});
