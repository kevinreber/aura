// Retry configuration
const RETRY_CONFIG = {
  maxRetries: 3,
  baseDelayMs: 1000, // 1 second
  maxDelayMs: 8000, // 8 seconds
};

// Sleep utility for retry delays
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Calculate exponential backoff delay
const getBackoffDelay = (attempt: number): number => {
  const delay = RETRY_CONFIG.baseDelayMs * Math.pow(2, attempt);
  return Math.min(delay, RETRY_CONFIG.maxDelayMs);
};

// Check if error is retryable (network errors, 5xx, 429)
const isRetryableError = (error: unknown, response?: Response): boolean => {
  // Network errors are retryable
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return true;
  }
  // 5xx server errors and 429 rate limiting are retryable
  if (response && (response.status >= 500 || response.status === 429)) {
    return true;
  }
  return false;
};

// API client for communicating with the AI Agent
export class AIAgentAPI {
  private baseURL: string;

  constructor() {
    // Use environment variable if set, otherwise default to localhost
    this.baseURL = import.meta.env?.VITE_AI_AGENT_API_URL || 'http://localhost:8001';

    if (import.meta.env?.VITE_DEBUG === 'true') {
      console.log(`🔗 AI Agent API URL: ${this.baseURL}`);
      console.log(`🌍 Environment: ${import.meta.env?.VITE_ENVIRONMENT}`);
    }
  }

  private async fetchAPI(endpoint: string, options: RequestInit = {}): Promise<any> {
    const url = `${this.baseURL}${endpoint}`;
    let lastError: Error | null = null;
    let lastResponse: Response | undefined;

    for (let attempt = 0; attempt <= RETRY_CONFIG.maxRetries; attempt++) {
      try {
        const response = await fetch(url, {
          headers: {
            'Content-Type': 'application/json',
            ...options.headers,
          },
          ...options,
        });

        lastResponse = response;

        if (!response.ok) {
          const error = new Error(`API Error: ${response.status} ${response.statusText}`);
          if (isRetryableError(error, response) && attempt < RETRY_CONFIG.maxRetries) {
            const delay = getBackoffDelay(attempt);
            console.warn(`Request failed (attempt ${attempt + 1}/${RETRY_CONFIG.maxRetries + 1}), retrying in ${delay}ms...`);
            await sleep(delay);
            continue;
          }
          throw error;
        }

        return response.json();
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));

        if (isRetryableError(error, lastResponse) && attempt < RETRY_CONFIG.maxRetries) {
          const delay = getBackoffDelay(attempt);
          console.warn(`Request failed (attempt ${attempt + 1}/${RETRY_CONFIG.maxRetries + 1}), retrying in ${delay}ms...`);
          await sleep(delay);
          continue;
        }

        throw lastError;
      }
    }

    throw lastError || new Error('Request failed after retries');
  }

  // Weather data
  async getWeather(location: string = 'San Francisco'): Promise<WeatherData> {
    try {
      const params = new URLSearchParams({ location, when: 'today' });
      return await this.fetchAPI(`/tools/weather?${params}`);
    } catch (error) {
      console.warn('Failed to fetch weather data:', error);
      return this.getMockWeather();
    }
  }

  // Financial data
  async getFinancialData(
    symbols: string[] = ['MSFT', 'BTC', 'ETH', 'NVDA']
  ): Promise<FinancialData> {
    try {
      return await this.fetchAPI('/tools/financial', {
        method: 'POST',
        body: JSON.stringify({
          symbols,
          data_type: 'mixed',
        }),
      });
    } catch (error) {
      console.warn('Failed to fetch financial data:', error);
      return this.getMockFinancial();
    }
  }

  // Calendar data
  async getCalendar(date?: string): Promise<CalendarData> {
    try {
      const params = new URLSearchParams();
      if (date) params.append('date', date);
      return await this.fetchAPI(`/tools/calendar?${params}`);
    } catch (error) {
      console.warn('Failed to fetch calendar data:', error);
      return this.getMockCalendar();
    }
  }

  // Todo data
  async getTodos(bucket?: string): Promise<TodoData> {
    try {
      const params: any = {};
      if (bucket) {
        params.bucket = bucket;
      }

      const queryString = Object.keys(params).length > 0 ? `?${new URLSearchParams(params)}` : '';

      return await this.fetchAPI(`/tools/todos${queryString}`);
    } catch (error) {
      console.warn('Failed to fetch todo data:', error);
      return this.getMockTodos(bucket);
    }
  }

  // AI Chat
  async sendChatMessage(message: string): Promise<ChatResponse> {
    try {
      return await this.fetchAPI('/chat', {
        method: 'POST',
        body: JSON.stringify({ message }),
      });
    } catch (error) {
      console.warn('Failed to send chat message:', error);
      throw error;
    }
  }

  // Get morning briefing
  async getMorningBriefing(): Promise<BriefingData> {
    try {
      return await this.fetchAPI('/briefing?type=smart');
    } catch (error) {
      console.warn('Failed to fetch morning briefing:', error);
      return this.getMockBriefing();
    }
  }

  // Traffic/Commute methods
  async getBasicCommute(
    origin: string,
    destination: string,
    mode: string = 'driving'
  ): Promise<BasicCommuteData> {
    try {
      return await this.fetchAPI('/tools/commute', {
        method: 'POST',
        body: JSON.stringify({
          origin,
          destination,
          mode,
        }),
      });
    } catch (error) {
      console.warn('Failed to fetch basic commute data:', error);
      return this.getMockBasicCommute();
    }
  }

  async getCommuteOptions(
    direction: string,
    departureTime?: string,
    includeDriving: boolean = true,
    includeTransit: boolean = true
  ): Promise<CommuteOptionsData> {
    try {
      const body: any = {
        direction,
        include_driving: includeDriving,
        include_transit: includeTransit,
      };
      if (departureTime) {
        body.departure_time = departureTime;
      }

      return await this.fetchAPI('/tools/commute-options', {
        method: 'POST',
        body: JSON.stringify(body),
      });
    } catch (error) {
      console.warn('Failed to fetch commute options:', error);
      return this.getMockCommuteOptions();
    }
  }

  async getShuttleSchedule(
    origin: string,
    destination: string,
    departureTime?: string
  ): Promise<ShuttleScheduleData> {
    try {
      const body: any = {
        origin,
        destination,
      };
      if (departureTime) {
        body.departure_time = departureTime;
      }

      return await this.fetchAPI('/tools/shuttle', {
        method: 'POST',
        body: JSON.stringify(body),
      });
    } catch (error) {
      console.warn('Failed to fetch shuttle schedule:', error);
      return this.getMockShuttleSchedule();
    }
  }

  // Fallback mock data methods
  private getMockWeather(): WeatherData {
    return {
      tool: 'weather',
      data: {
        location: 'San Francisco',
        current_temp: 72,
        condition: 'Partly Cloudy',
        temp_hi: 78,
        temp_lo: 65,
        precip_chance: 10,
        summary: 'Partly cloudy with comfortable temperatures',
      },
      timestamp: new Date().toISOString(),
    };
  }

  private getMockFinancial(): FinancialData {
    return {
      tool: 'financial',
      data: {
        summary: '📊 4 instruments tracked | 📈 3 gaining | 🏆 Best: NVDA (+2.1%)',
        total_items: 4,
        market_status: 'mixed',
        data: [
          {
            symbol: 'MSFT',
            name: 'Microsoft Corporation',
            price: 523.73,
            change: 6.23,
            change_percent: 1.2,
            currency: 'USD',
            data_type: 'stocks',
          },
          {
            symbol: 'BTC',
            name: 'Bitcoin',
            price: 96847,
            change: -2284,
            change_percent: -2.3,
            currency: 'USD',
            data_type: 'crypto',
          },
          {
            symbol: 'ETH',
            name: 'Ethereum',
            price: 2847,
            change: 42,
            change_percent: 1.5,
            currency: 'USD',
            data_type: 'crypto',
          },
          {
            symbol: 'NVDA',
            name: 'NVIDIA Corporation',
            price: 875.12,
            change: 18.2,
            change_percent: 2.1,
            currency: 'USD',
            data_type: 'stocks',
          },
        ],
      },
      timestamp: new Date().toISOString(),
    };
  }

  private getMockCalendar(): CalendarData {
    return {
      tool: 'calendar',
      data: {
        events: [
          { title: 'Team Standup', time: '9:00 AM', color: 'blue' },
          { title: 'Code Review', time: '2:00 PM', color: 'green' },
          { title: 'Gym Session', time: '6:00 PM', color: 'orange' },
        ],
        total_events: 3,
      },
      timestamp: new Date().toISOString(),
    };
  }

  private getMockTodos(bucket?: string): TodoData {
    const allTodos = [
      {
        id: '1',
        text: 'Review quarterly reports',
        completed: false,
        priority: 'high',
        bucket: 'work',
      },
      {
        id: '2',
        text: 'Update project timeline',
        completed: false,
        priority: 'medium',
        bucket: 'work',
      },
      {
        id: '3',
        text: 'Call insurance company',
        completed: false,
        priority: 'low',
        bucket: 'personal',
      },
      {
        id: '4',
        text: 'Book dentist appointment',
        completed: false,
        priority: 'low',
        bucket: 'personal',
      },
      { id: '5', text: 'Grocery shopping', completed: false, priority: 'medium', bucket: 'home' },
      {
        id: '6',
        text: 'Pick up dry cleaning',
        completed: false,
        priority: 'low',
        bucket: 'errands',
      },
    ];

    const items = bucket ? allTodos.filter((todo) => todo.bucket === bucket) : allTodos;

    return {
      tool: 'todos',
      data: {
        items: items.map(({ bucket, ...item }) => item), // Remove bucket from items for compatibility
        total_pending: items.filter((item) => !item.completed).length,
        bucket: bucket || null,
      },
      timestamp: new Date().toISOString(),
    };
  }

  private getMockBriefing(): BriefingData {
    return {
      briefing:
        "Good morning! Here's your daily overview: Weather is pleasant at 72°F. Markets are mixed with NVDA leading gains. You have 3 meetings today and 4 pending tasks.",
      timestamp: new Date().toISOString(),
    };
  }

  private getMockBasicCommute(): BasicCommuteData {
    return {
      tool: 'commute',
      data: {
        duration_minutes: 35,
        distance_miles: 18.2,
        route_summary: 'via US-101 S and I-880 S',
        traffic_status: 'Moderate traffic',
        origin: 'San Francisco, CA',
        destination: 'Mountain View, CA',
        mode: 'driving',
      },
      timestamp: new Date().toISOString(),
    };
  }

  private getMockCommuteOptions(): CommuteOptionsData {
    return {
      tool: 'commute_options',
      data: {
        direction: 'to_work',
        query_time: new Date().toISOString(),
        driving: {
          duration_minutes: 42,
          distance_miles: 28.5,
          route_summary: 'South SF → LinkedIn',
          traffic_status: 'Heavy traffic',
          departure_time: '8:00 AM',
          arrival_time: '8:42 AM',
          estimated_fuel_gallons: 1.1,
        },
        transit: {
          total_duration_minutes: 85,
          caltrain_duration_minutes: 47,
          shuttle_duration_minutes: 11,
          walking_duration_minutes: 3,
          next_departures: [
            {
              departure_time: '8:15 AM',
              arrival_time: '9:02 AM',
              train_number: '152',
              platform: 'TBD',
              delay_minutes: 0,
            },
            {
              departure_time: '8:45 AM',
              arrival_time: '9:32 AM',
              train_number: '156',
              platform: 'TBD',
              delay_minutes: 2,
            },
          ],
          shuttle_departures: [
            {
              departure_time: '9:11 AM',
              stops: ['9:11 AM', '9:19 AM', '9:22 AM'],
            },
            {
              departure_time: '9:26 AM',
              stops: ['9:26 AM', '9:34 AM', '9:37 AM'],
            },
          ],
          transfer_time_minutes: 5,
        },
        recommendation:
          'Take Caltrain - heavy traffic makes driving significantly slower (42 min vs 85 min total)',
      },
      timestamp: new Date().toISOString(),
    };
  }

  private getMockShuttleSchedule(): ShuttleScheduleData {
    return {
      tool: 'shuttle',
      data: {
        origin: 'mountain_view_caltrain',
        destination: 'linkedin_transit_center',
        duration_minutes: 11,
        next_departures: [
          {
            departure_time: '9:11 AM',
            stops: ['9:11 AM', '9:19 AM', '9:22 AM'],
          },
          {
            departure_time: '9:26 AM',
            stops: ['9:26 AM', '9:34 AM', '9:37 AM'],
          },
          {
            departure_time: '9:41 AM',
            stops: ['9:41 AM', '9:49 AM', '9:52 AM'],
          },
        ],
        service_hours: '6:00 AM - 10:00 PM',
        frequency_minutes: '15',
      },
      timestamp: new Date().toISOString(),
    };
  }
}

// Type definitions
export interface WeatherData {
  tool: string;
  data: {
    location: string;
    current_temp: number;
    condition: string;
    temp_hi: number;
    temp_lo: number;
    precip_chance: number;
    summary: string;
  };
  timestamp: string;
}

export interface FinancialData {
  tool: string;
  data: {
    summary: string;
    total_items: number;
    market_status: string;
    data: Array<{
      symbol: string;
      name: string;
      price: number;
      change: number;
      change_percent: number;
      currency: string;
      data_type: string;
    }>;
  };
  timestamp: string;
}

export interface CalendarData {
  tool: string;
  data: {
    events: Array<{
      title: string;
      time: string;
      color: string;
    }>;
    total_events: number;
  };
  timestamp: string;
}

export interface TodoData {
  tool: string;
  data: {
    items: Array<{
      id: string;
      text: string;
      completed: boolean;
      priority: string;
    }>;
    total_pending: number;
    bucket?: string | null; // Added bucket field
  };
  timestamp: string;
}

// Available todo buckets
export type TodoBucket = 'work' | 'home' | 'errands' | 'personal';

export interface ChatResponse {
  response: string;
  timestamp: string;
}

export interface BriefingData {
  briefing: string;
  timestamp: string;
}

// Traffic/Commute data interfaces
export interface BasicCommuteData {
  tool: string;
  data: {
    duration_minutes: number;
    distance_miles: number;
    route_summary: string;
    traffic_status: string;
    origin: string;
    destination: string;
    mode: string;
  };
  timestamp: string;
}

export interface DrivingOption {
  duration_minutes: number;
  distance_miles: number;
  route_summary: string;
  traffic_status: string;
  departure_time: string;
  arrival_time: string;
  estimated_fuel_gallons: number;
}

export interface CaltrainDeparture {
  departure_time: string;
  arrival_time: string;
  train_number: string;
  platform?: string;
  delay_minutes: number;
}

export interface ShuttleDeparture {
  departure_time: string;
  stops: string[];
}

export interface TransitOption {
  total_duration_minutes: number;
  caltrain_duration_minutes: number;
  shuttle_duration_minutes: number;
  walking_duration_minutes: number;
  next_departures: CaltrainDeparture[];
  shuttle_departures: ShuttleDeparture[];
  transfer_time_minutes: number;
}

export interface CommuteOptionsData {
  tool: string;
  data: {
    direction: string;
    query_time: string;
    driving?: DrivingOption;
    transit?: TransitOption;
    recommendation: string;
  };
  timestamp: string;
}

export interface ShuttleScheduleData {
  tool: string;
  data: {
    origin: string;
    destination: string;
    duration_minutes: number;
    next_departures: ShuttleDeparture[];
    service_hours: string;
    frequency_minutes: string;
  };
  timestamp: string;
}

// Create a singleton instance
export const apiClient = new AIAgentAPI();

// Server-side API client (uses Node.js environment variables)
export class ServerAIAgentAPI {
  private baseURL: string;

  constructor() {
    // Use Node.js environment variables for server-side
    // Only access process.env on server-side (Node.js environment)
    if (typeof window === 'undefined') {
      this.baseURL = process.env.VITE_AI_AGENT_API_URL || 'http://localhost:8001';

      if (process.env.VITE_DEBUG === 'true') {
        console.log(`🔗 Server AI Agent API URL: ${this.baseURL}`);
      }
    } else {
      // Fallback for browser (shouldn't be used)
      this.baseURL = 'http://localhost:8001';
    }
  }

  private async fetchAPI(endpoint: string, options: RequestInit = {}): Promise<any> {
    const url = `${this.baseURL}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // Weather data
  async getWeather(location: string = 'San Francisco'): Promise<WeatherData> {
    try {
      const params = new URLSearchParams({ location, when: 'today' });
      return await this.fetchAPI(`/tools/weather?${params}`);
    } catch (error) {
      console.warn('Failed to fetch weather data:', error);
      throw error;
    }
  }

  // Financial data
  async getFinancialData(
    symbols: string[] = ['MSFT', 'BTC', 'ETH', 'NVDA']
  ): Promise<FinancialData> {
    try {
      return await this.fetchAPI('/tools/financial', {
        method: 'POST',
        body: JSON.stringify({
          symbols,
          data_type: 'mixed',
        }),
      });
    } catch (error) {
      console.warn('Failed to fetch financial data:', error);
      throw error;
    }
  }

  // Calendar data
  async getCalendar(date?: string): Promise<CalendarData> {
    try {
      const params = new URLSearchParams();
      if (date) params.append('date', date);
      return await this.fetchAPI(`/tools/calendar?${params}`);
    } catch (error) {
      console.warn('Failed to fetch calendar data:', error);
      throw error;
    }
  }

  // Todo data
  async getTodos(bucket?: string): Promise<TodoData> {
    try {
      const params: any = {};
      if (bucket) {
        params.bucket = bucket;
      }

      const queryString = Object.keys(params).length > 0 ? `?${new URLSearchParams(params)}` : '';

      return await this.fetchAPI(`/tools/todos${queryString}`);
    } catch (error) {
      console.warn('Failed to fetch todo data:', error);
      throw error;
    }
  }

  // AI Chat (server-side)
  async sendChatMessage(message: string): Promise<ChatResponse> {
    try {
      return await this.fetchAPI('/chat', {
        method: 'POST',
        body: JSON.stringify({ message }),
      });
    } catch (error) {
      console.warn('Failed to send chat message:', error);
      throw error;
    }
  }

  // Traffic/Commute methods (server-side)
  async getBasicCommute(
    origin: string,
    destination: string,
    mode: string = 'driving'
  ): Promise<BasicCommuteData> {
    try {
      return await this.fetchAPI('/tools/commute', {
        method: 'POST',
        body: JSON.stringify({
          origin,
          destination,
          mode,
        }),
      });
    } catch (error) {
      console.warn('Failed to fetch basic commute data:', error);
      throw error;
    }
  }

  async getCommuteOptions(
    direction: string,
    departureTime?: string,
    includeDriving: boolean = true,
    includeTransit: boolean = true
  ): Promise<CommuteOptionsData> {
    try {
      const body: any = {
        direction,
        include_driving: includeDriving,
        include_transit: includeTransit,
      };
      if (departureTime) {
        body.departure_time = departureTime;
      }

      return await this.fetchAPI('/tools/commute-options', {
        method: 'POST',
        body: JSON.stringify(body),
      });
    } catch (error) {
      console.warn('Failed to fetch commute options:', error);
      throw error;
    }
  }

  async getShuttleSchedule(
    origin: string,
    destination: string,
    departureTime?: string
  ): Promise<ShuttleScheduleData> {
    try {
      const body: any = {
        origin,
        destination,
      };
      if (departureTime) {
        body.departure_time = departureTime;
      }

      return await this.fetchAPI('/tools/shuttle', {
        method: 'POST',
        body: JSON.stringify(body),
      });
    } catch (error) {
      console.warn('Failed to fetch shuttle schedule:', error);
      throw error;
    }
  }
}

// Server-side instance
export const serverApiClient = new ServerAIAgentAPI();
