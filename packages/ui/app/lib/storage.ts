// Local storage utilities for persisting app state

const STORAGE_KEYS = {
  CHAT_HISTORY: 'daily-agent-chat-history',
  TODO_COMPLETIONS: 'daily-agent-todo-completions',
  SELECTED_BUCKET: 'daily-agent-selected-bucket',
  DARK_MODE: 'daily-agent-dark-mode',
  NOTES: 'daily-agent-notes',
  HABITS: 'daily-agent-habits',
  HABIT_LOGS: 'daily-agent-habit-logs',
  POMODORO_SETTINGS: 'daily-agent-pomodoro-settings',
  API_CACHE: 'daily-agent-api-cache',
} as const;

type ChatMessage = {
  type: 'user' | 'ai';
  message: string;
  timestamp: string;
};

// Check if we're in a browser environment
const isBrowser = typeof window !== 'undefined';

// Chat History persistence
export function saveChatHistory(history: ChatMessage[]): void {
  if (!isBrowser) return;
  try {
    // Keep only the last 50 messages to prevent localStorage from getting too large
    const trimmedHistory = history.slice(-50);
    localStorage.setItem(STORAGE_KEYS.CHAT_HISTORY, JSON.stringify(trimmedHistory));
  } catch (error) {
    console.warn('Failed to save chat history to localStorage:', error);
  }
}

export function loadChatHistory(): ChatMessage[] {
  if (!isBrowser) return [];
  try {
    const stored = localStorage.getItem(STORAGE_KEYS.CHAT_HISTORY);
    if (stored) {
      return JSON.parse(stored) as ChatMessage[];
    }
  } catch (error) {
    console.warn('Failed to load chat history from localStorage:', error);
  }
  return [];
}

export function clearChatHistory(): void {
  if (!isBrowser) return;
  try {
    localStorage.removeItem(STORAGE_KEYS.CHAT_HISTORY);
  } catch (error) {
    console.warn('Failed to clear chat history from localStorage:', error);
  }
}

// Todo completions persistence (only stores completion state, not the full todo)
export function saveTodoCompletions(completions: Record<string, boolean>): void {
  if (!isBrowser) return;
  try {
    localStorage.setItem(STORAGE_KEYS.TODO_COMPLETIONS, JSON.stringify(completions));
  } catch (error) {
    console.warn('Failed to save todo completions to localStorage:', error);
  }
}

export function loadTodoCompletions(): Record<string, boolean> {
  if (!isBrowser) return {};
  try {
    const stored = localStorage.getItem(STORAGE_KEYS.TODO_COMPLETIONS);
    if (stored) {
      return JSON.parse(stored) as Record<string, boolean>;
    }
  } catch (error) {
    console.warn('Failed to load todo completions from localStorage:', error);
  }
  return {};
}

export function toggleTodoCompletion(todoId: string, completed: boolean): Record<string, boolean> {
  const current = loadTodoCompletions();
  const updated = { ...current, [todoId]: completed };
  saveTodoCompletions(updated);
  return updated;
}

// Bucket selection persistence
export function saveSelectedBucket(bucket: string): void {
  if (!isBrowser) return;
  try {
    localStorage.setItem(STORAGE_KEYS.SELECTED_BUCKET, bucket);
  } catch (error) {
    console.warn('Failed to save selected bucket to localStorage:', error);
  }
}

export function loadSelectedBucket(): string | null {
  if (!isBrowser) return null;
  try {
    return localStorage.getItem(STORAGE_KEYS.SELECTED_BUCKET);
  } catch (error) {
    console.warn('Failed to load selected bucket from localStorage:', error);
  }
  return null;
}

// Dark mode persistence
export function saveDarkMode(isDark: boolean): void {
  if (!isBrowser) return;
  try {
    localStorage.setItem(STORAGE_KEYS.DARK_MODE, JSON.stringify(isDark));
    // Also update the document class for Tailwind
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  } catch (error) {
    console.warn('Failed to save dark mode to localStorage:', error);
  }
}

export function loadDarkMode(): boolean | null {
  if (!isBrowser) return null;
  try {
    const stored = localStorage.getItem(STORAGE_KEYS.DARK_MODE);
    if (stored !== null) {
      return JSON.parse(stored) as boolean;
    }
    // Check system preference as fallback
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  } catch (error) {
    console.warn('Failed to load dark mode from localStorage:', error);
  }
  return null;
}

export function initializeDarkMode(): boolean {
  const isDark = loadDarkMode() ?? false;
  if (isBrowser) {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }
  return isDark;
}

// Notes persistence
export type Note = {
  id: string;
  content: string;
  createdAt: string;
  updatedAt: string;
};

export function saveNotes(notes: Note[]): void {
  if (!isBrowser) return;
  try {
    localStorage.setItem(STORAGE_KEYS.NOTES, JSON.stringify(notes));
  } catch (error) {
    console.warn('Failed to save notes to localStorage:', error);
  }
}

export function loadNotes(): Note[] {
  if (!isBrowser) return [];
  try {
    const stored = localStorage.getItem(STORAGE_KEYS.NOTES);
    if (stored) {
      return JSON.parse(stored) as Note[];
    }
  } catch (error) {
    console.warn('Failed to load notes from localStorage:', error);
  }
  return [];
}

// Habits persistence
export type Habit = {
  id: string;
  name: string;
  icon: string;
  createdAt: string;
};

export type HabitLog = {
  habitId: string;
  date: string; // YYYY-MM-DD format
  completed: boolean;
};

export function saveHabits(habits: Habit[]): void {
  if (!isBrowser) return;
  try {
    localStorage.setItem(STORAGE_KEYS.HABITS, JSON.stringify(habits));
  } catch (error) {
    console.warn('Failed to save habits to localStorage:', error);
  }
}

export function loadHabits(): Habit[] {
  if (!isBrowser) return [];
  try {
    const stored = localStorage.getItem(STORAGE_KEYS.HABITS);
    if (stored) {
      return JSON.parse(stored) as Habit[];
    }
  } catch (error) {
    console.warn('Failed to load habits from localStorage:', error);
  }
  return [];
}

export function saveHabitLogs(logs: HabitLog[]): void {
  if (!isBrowser) return;
  try {
    // Keep only last 90 days of logs
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - 90);
    const cutoffStr = cutoffDate.toISOString().split('T')[0];
    const filteredLogs = logs.filter((log) => log.date >= cutoffStr);
    localStorage.setItem(STORAGE_KEYS.HABIT_LOGS, JSON.stringify(filteredLogs));
  } catch (error) {
    console.warn('Failed to save habit logs to localStorage:', error);
  }
}

export function loadHabitLogs(): HabitLog[] {
  if (!isBrowser) return [];
  try {
    const stored = localStorage.getItem(STORAGE_KEYS.HABIT_LOGS);
    if (stored) {
      return JSON.parse(stored) as HabitLog[];
    }
  } catch (error) {
    console.warn('Failed to load habit logs from localStorage:', error);
  }
  return [];
}

export function getHabitStreak(habitId: string, logs: HabitLog[]): number {
  const today = new Date().toISOString().split('T')[0];
  const habitLogs = logs
    .filter((log) => log.habitId === habitId && log.completed)
    .map((log) => log.date)
    .sort()
    .reverse();

  if (habitLogs.length === 0) return 0;

  let streak = 0;
  const checkDate = new Date(today);

  // If not completed today, start from yesterday
  if (!habitLogs.includes(today)) {
    checkDate.setDate(checkDate.getDate() - 1);
  }

  while (true) {
    const dateStr = checkDate.toISOString().split('T')[0];
    if (habitLogs.includes(dateStr)) {
      streak++;
      checkDate.setDate(checkDate.getDate() - 1);
    } else {
      break;
    }
  }

  return streak;
}

// Pomodoro settings persistence
export type PomodoroSettings = {
  workDuration: number; // minutes
  breakDuration: number; // minutes
  longBreakDuration: number; // minutes
  sessionsBeforeLongBreak: number;
};

export const DEFAULT_POMODORO_SETTINGS: PomodoroSettings = {
  workDuration: 25,
  breakDuration: 5,
  longBreakDuration: 15,
  sessionsBeforeLongBreak: 4,
};

export function savePomodoroSettings(settings: PomodoroSettings): void {
  if (!isBrowser) return;
  try {
    localStorage.setItem(STORAGE_KEYS.POMODORO_SETTINGS, JSON.stringify(settings));
  } catch (error) {
    console.warn('Failed to save pomodoro settings to localStorage:', error);
  }
}

export function loadPomodoroSettings(): PomodoroSettings {
  if (!isBrowser) return DEFAULT_POMODORO_SETTINGS;
  try {
    const stored = localStorage.getItem(STORAGE_KEYS.POMODORO_SETTINGS);
    if (stored) {
      return { ...DEFAULT_POMODORO_SETTINGS, ...JSON.parse(stored) };
    }
  } catch (error) {
    console.warn('Failed to load pomodoro settings from localStorage:', error);
  }
  return DEFAULT_POMODORO_SETTINGS;
}

// API Cache for client-side caching with TTL
type CacheEntry<T> = {
  data: T;
  timestamp: number;
  ttl: number; // milliseconds
};

type CacheStore = Record<string, CacheEntry<unknown>>;

export function getCachedData<T>(key: string): T | null {
  if (!isBrowser) return null;
  try {
    const stored = localStorage.getItem(STORAGE_KEYS.API_CACHE);
    if (!stored) return null;

    const cache = JSON.parse(stored) as CacheStore;
    const entry = cache[key] as CacheEntry<T> | undefined;

    if (!entry) return null;

    // Check if cache is still valid
    if (Date.now() - entry.timestamp > entry.ttl) {
      // Cache expired, remove it
      delete cache[key];
      localStorage.setItem(STORAGE_KEYS.API_CACHE, JSON.stringify(cache));
      return null;
    }

    return entry.data;
  } catch (error) {
    console.warn('Failed to get cached data:', error);
  }
  return null;
}

export function setCachedData<T>(key: string, data: T, ttlMs: number): void {
  if (!isBrowser) return;
  try {
    const stored = localStorage.getItem(STORAGE_KEYS.API_CACHE);
    const cache: CacheStore = stored ? JSON.parse(stored) : {};

    cache[key] = {
      data,
      timestamp: Date.now(),
      ttl: ttlMs,
    };

    localStorage.setItem(STORAGE_KEYS.API_CACHE, JSON.stringify(cache));
  } catch (error) {
    console.warn('Failed to set cached data:', error);
  }
}

export function clearApiCache(): void {
  if (!isBrowser) return;
  try {
    localStorage.removeItem(STORAGE_KEYS.API_CACHE);
  } catch (error) {
    console.warn('Failed to clear API cache:', error);
  }
}
