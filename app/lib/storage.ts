// Local storage utilities for persisting app state

const STORAGE_KEYS = {
  CHAT_HISTORY: 'daily-agent-chat-history',
  TODO_COMPLETIONS: 'daily-agent-todo-completions',
  SELECTED_BUCKET: 'daily-agent-selected-bucket',
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
