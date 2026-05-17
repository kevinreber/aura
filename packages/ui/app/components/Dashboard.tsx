import { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Component overrides shared between the chat-history and streaming
// ReactMarkdown instances. Tailwind classes match the chat bubble's `text-sm`.
const MARKDOWN_COMPONENTS = {
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className="mb-2 last:mb-0">{children}</p>
  ),
  h1: ({ children }: { children?: React.ReactNode }) => (
    <h1 className="text-base font-semibold mt-3 mb-2 first:mt-0">{children}</h1>
  ),
  h2: ({ children }: { children?: React.ReactNode }) => (
    <h2 className="text-sm font-semibold mt-3 mb-1.5 first:mt-0">{children}</h2>
  ),
  h3: ({ children }: { children?: React.ReactNode }) => (
    <h3 className="text-sm font-semibold mt-2.5 mb-1 first:mt-0 text-gray-800 dark:text-gray-100">
      {children}
    </h3>
  ),
  h4: ({ children }: { children?: React.ReactNode }) => (
    <h4 className="text-sm font-medium mt-2 mb-1 first:mt-0">{children}</h4>
  ),
  ul: ({ children }: { children?: React.ReactNode }) => (
    <ul className="list-disc pl-4 mb-2 space-y-0.5">{children}</ul>
  ),
  ol: ({ children }: { children?: React.ReactNode }) => (
    <ol className="list-decimal pl-4 mb-2 space-y-0.5">{children}</ol>
  ),
  li: ({ children }: { children?: React.ReactNode }) => <li className="mb-1">{children}</li>,
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong className="font-semibold">{children}</strong>
  ),
  em: ({ children }: { children?: React.ReactNode }) => <em className="italic">{children}</em>,
  code: ({ children }: { children?: React.ReactNode }) => (
    <code className="bg-gray-200 dark:bg-gray-600 px-1 py-0.5 rounded text-xs">{children}</code>
  ),
  a: ({ href, children }: { href?: string; children?: React.ReactNode }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-blue-600 dark:text-blue-400 hover:underline"
    >
      {children}
    </a>
  ),
  hr: () => <hr className="my-2 border-gray-300 dark:border-gray-600" />,
};

const REMARK_PLUGINS = [remarkGfm];

// LLMs (especially GPT-4o-mini) sometimes generate markdown without proper
// line breaks between sections, e.g.:
//   "intro:### Day 1:- item"        (header missing newline)
//   "Adventures**Morning:**"        (bold section-header glued to prior text)
//   "★ 4.8**Lunch:**"               (rating glued to next bold section header)
// Markdown specs require headers and list items to start on their own line.
// We defensively inject newlines so structured responses render correctly
// even when the LLM emits concatenated output.
function normalizeMarkdown(text: string): string {
  if (!text) return text;
  return (
    text
      // ATX headers that appear mid-line: "foo### Bar" → "foo\n\n### Bar"
      .replace(/([^\n])(#{1,6} )/g, '$1\n\n$2')
      // Bold "section header" patterns — **CapitalStart...colonEnd** —
      // when preceded by non-newline non-asterisk content. Catches the
      // "Adventures**Morning:**" and "4.8**Lunch:**" cases without
      // breaking valid mid-sentence bold (which usually doesn't end in ":").
      .replace(/([^\n*])(\*\*[A-Z][^*\n]{1,50}:\*\*)/g, '$1\n\n$2')
      // List items: "text- Item" → "text\n- Item"
      .replace(/([^\n\s])(- (?=[A-Z*_]))/g, '$1\n$2')
  );
}
import { useDarkMode } from '../hooks/useDarkMode';
import { usePolling } from '../hooks/usePolling';
import {
  apiClient,
  type CalendarData,
  type CommuteOptionsData,
  type FinancialData,
  type TodoBucket,
  type TodoData,
  type WeatherData,
} from '../lib/api';
import {
  clearChatHistory,
  getCachedData,
  loadChatHistory,
  loadSelectedBucket,
  loadTodoCompletions,
  saveChatHistory,
  saveSelectedBucket,
  setCachedData,
  toggleTodoCompletion,
} from '../lib/storage';
import Clock from './Clock';
import { CommuteDashboard } from './CommuteDashboard';
import { HabitsWidget } from './HabitsWidget';
import { NotesWidget } from './NotesWidget';
import { PomodoroWidget } from './PomodoroWidget';
import { WeekendPlannerWidget } from './WeekendPlannerWidget';
import { WeekendSettings } from './WeekendSettings';

// Shared card styling — refined glass-morphism look that adapts to light/dark.
const CARD_BASE =
  'group rounded-2xl border border-slate-200/70 bg-white/80 shadow-sm shadow-slate-200/40 backdrop-blur-sm transition-all hover:border-slate-300 hover:shadow-md dark:border-white/10 dark:bg-white/[0.04] dark:shadow-none dark:hover:border-white/20';

const CHEVRON_BTN =
  'rounded-md p-1 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:hover:bg-white/10 dark:hover:text-white';

function SectionHeader({
  title,
  subtitle,
  tag,
}: {
  title: string;
  subtitle?: string;
  tag?: string;
}) {
  return (
    <div className="mb-3 flex items-baseline justify-between gap-3">
      <div className="min-w-0">
        <h3 className="text-sm font-semibold tracking-wide text-slate-900 dark:text-white">
          {title}
        </h3>
        {subtitle && (
          <p className="text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>
        )}
      </div>
      {tag && (
        <span className="flex-shrink-0 text-xs font-medium uppercase tracking-wider text-slate-400 dark:text-slate-500">
          {tag}
        </span>
      )}
    </div>
  );
}

interface DashboardProps {
  userName?: string;
  userEmail?: string;
  userPicture?: string;
  // Server-side loaded data (no CORS issues!)
  initialWeather?: WeatherData | null;
  initialFinancial?: FinancialData | null;
  initialCalendar?: CalendarData | null;
  initialTodos?: TodoData | null;
  initialCommute?: CommuteOptionsData | null;
  serverErrors?: {
    weather?: string | null;
    financial?: string | null;
    calendar?: string | null;
    todos?: string | null;
    commute?: string | null;
  };
}

// Agent returns ISO-ish "YYYY-MM-DD HH:MM:SS" or all_day events. Format to "h:mm AM/PM"
// for the dashboard widget without pulling in a date lib.
function formatEventTime(event: { start_time?: string; all_day?: boolean }): string {
  if (event.all_day) return 'All day';
  if (!event.start_time) return '';
  // Accept either "YYYY-MM-DD HH:MM:SS" or ISO 8601.
  const isoish = event.start_time.includes('T')
    ? event.start_time
    : event.start_time.replace(' ', 'T');
  const d = new Date(isoish);
  if (Number.isNaN(d.getTime())) return event.start_time;
  return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

export default function Dashboard({
  userName = 'Kevin',
  userEmail,
  userPicture,
  initialWeather,
  initialFinancial,
  initialCalendar,
  initialTodos,
  initialCommute,
  serverErrors,
}: DashboardProps) {
  const [weather, setWeather] = useState<WeatherData | null>(initialWeather || null);
  const [financial, setFinancial] = useState<FinancialData | null>(initialFinancial || null);
  const [calendar, setCalendar] = useState<CalendarData | null>(initialCalendar || null);
  const [todos, setTodos] = useState<TodoData | null>(initialTodos || null);
  const [selectedBucket, setSelectedBucket] = useState<TodoBucket | 'all'>(() => {
    const saved = loadSelectedBucket();
    return (saved as TodoBucket | 'all') || 'all';
  });
  const [chatMessage, setChatMessage] = useState('');
  const [weekendSettingsOpen, setWeekendSettingsOpen] = useState(false);
  // Bumped whenever weekend prefs change so the planner widget refetches.
  const [weekendPrefsVersion, setWeekendPrefsVersion] = useState(0);
  const [chatHistory, setChatHistory] = useState<
    Array<{ type: 'user' | 'ai'; message: string; timestamp: string }>
  >(() => loadChatHistory());
  const [todoCompletions, setTodoCompletions] = useState<Record<string, boolean>>(() =>
    loadTodoCompletions()
  );
  const [loading, setLoading] = useState(
    !initialWeather && !initialFinancial && !initialCalendar && !initialTodos
  );
  const [isLoadingChat, setIsLoadingChat] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState<string>('');
  const [activeTools, setActiveTools] = useState<string[]>([]);
  const [agentStatus, setAgentStatus] = useState<'online' | 'offline' | 'checking'>('checking');
  const [showCommandSuggestions, setShowCommandSuggestions] = useState(false);
  const [selectedCommandIndex, setSelectedCommandIndex] = useState(0);

  // Ref for aborting streaming requests
  const abortControllerRef = useRef<AbortController | null>(null);

  // Dark mode
  const { isDark, toggle: toggleDarkMode } = useDarkMode();

  // Fetch financial data with caching. Goes through the UI proxy so the
  // session cookie carries auth — direct browser→Agent calls can't attach
  // the internal auth secret.
  const fetchFinancialData = useCallback(async () => {
    const cached = getCachedData<FinancialData>('financial');
    if (cached) return cached;

    const resp = await fetch('/api/v1/financial', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        symbols: ['MSFT', 'BTC', 'ETH', 'NVDA'],
        data_type: 'mixed',
      }),
    });
    if (!resp.ok) throw new Error(`financial ${resp.status}`);
    const data = (await resp.json()) as FinancialData;
    setCachedData('financial', data, 5 * 60 * 1000);
    return data;
  }, []);

  // Polling for real-time market updates (every 5 minutes)
  const { data: polledFinancial, lastUpdated: financialLastUpdated } = usePolling({
    fetcher: fetchFinancialData,
    interval: 5 * 60 * 1000, // 5 minutes
    enabled: !!initialFinancial, // Only poll if we have initial data
  });

  // Update financial data when polled data changes
  useEffect(() => {
    if (polledFinancial) {
      setFinancial(polledFinancial);
    }
  }, [polledFinancial]);

  // Slash command registry
  const slashCommands = [
    {
      command: '/summary',
      aliases: ['/briefing'],
      description: 'Get your daily morning briefing',
      icon: '📊',
      action: 'Give me a comprehensive morning briefing with weather, finance, calendar, and tasks',
    },
    {
      command: '/weather',
      aliases: ['/forecast'],
      description: 'Get current weather information',
      icon: '🌤️',
      action: "What's the current weather and forecast?",
    },
    {
      command: '/finance',
      aliases: ['/stocks', '/market'],
      description: 'Check your financial portfolio',
      icon: '💰',
      action: 'How are my stocks and crypto investments doing?',
    },
    {
      command: '/calendar',
      aliases: ['/schedule', '/events'],
      description: "View today's calendar events",
      icon: '📅',
      action: 'What events do I have scheduled for today?',
    },
    {
      command: '/tasks',
      aliases: ['/todos', '/todo'],
      description: 'Show your task list (try /tasks work or /tasks all)',
      icon: '✅',
      action: 'What tasks do I have to complete today?',
    },
    {
      command: '/commute',
      aliases: ['/traffic'],
      description: 'Check traffic and commute info',
      icon: '🚗',
      action: 'How does traffic to work look right now?',
    },
    {
      command: '/help',
      aliases: ['/commands'],
      description: 'Show available slash commands',
      icon: '❓',
      action: 'help', // Special case - handled locally
    },
  ];

  const [collapsedWidgets, setCollapsedWidgets] = useState<Record<string, boolean>>(() => {
    // On mobile, collapse some widgets by default for better UX
    const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
    return {
      weather: false,
      financial: isMobile,
      calendar: isMobile,
      todos: isMobile,
      notes: isMobile,
      habits: isMobile,
      pomodoro: isMobile,
      weekendPlanner: isMobile,
      chat: false, // Chat starts expanded
    };
  });
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat to bottom when new messages are added
  useEffect(() => {
    if (chatContainerRef.current) {
      const scrollElement = chatContainerRef.current;
      scrollElement.scrollTop = scrollElement.scrollHeight;
    }
  }, [chatHistory]);

  // Persist chat history to localStorage
  useEffect(() => {
    if (chatHistory.length > 0) {
      saveChatHistory(chatHistory);
    }
  }, [chatHistory]);

  // Persist selected bucket to localStorage
  useEffect(() => {
    saveSelectedBucket(selectedBucket);
  }, [selectedBucket]);

  // Check agent health periodically
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch('/api/v1/health', {
          method: 'GET',
          signal: AbortSignal.timeout(5000), // 5 second timeout
        });
        setAgentStatus(response.ok ? 'online' : 'offline');
      } catch {
        setAgentStatus('offline');
      }
    };

    // Check immediately on mount
    checkHealth();

    // Then check every 30 seconds
    const interval = setInterval(checkHealth, 30000);

    return () => clearInterval(interval);
  }, []);

  // Handle clearing chat history
  const handleClearChatHistory = () => {
    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    clearChatHistory();
    setStreamingMessage('');
    setActiveTools([]);
    setIsLoadingChat(false);
    setChatHistory([
      {
        type: 'ai',
        message: 'Chat history cleared. How can I help you today?',
        timestamp: new Date().toISOString(),
      },
    ]);
  };

  // Handle todo completion toggle with persistence
  const handleTodoToggle = (todoId: string, currentCompleted: boolean) => {
    const newCompleted = !currentCompleted;
    const updated = toggleTodoCompletion(todoId, newCompleted);
    setTodoCompletions(updated);
  };

  // Process slash commands
  const processSlashCommand = (input: string): string | null => {
    const trimmedInput = input.trim();
    if (!trimmedInput.startsWith('/')) return null;

    const commandPart = trimmedInput.split(' ')[0].toLowerCase();

    // Find matching command
    const matchedCommand = slashCommands.find(
      (cmd) => cmd.command === commandPart || cmd.aliases.includes(commandPart)
    );

    if (!matchedCommand) return null;

    // Handle special commands locally
    if (matchedCommand.action === 'help') {
      const helpMessage = `**Available Slash Commands:**\n\n${slashCommands
        .filter((cmd) => cmd.action !== 'help')
        .map(
          (cmd) =>
            `${cmd.icon} **${cmd.command}** ${cmd.aliases.length > 0 ? `(${cmd.aliases.join(', ')})` : ''}\n${cmd.description}`
        )
        .join('\n\n')}`;

      setChatHistory((prev) => [
        ...prev,
        {
          type: 'ai',
          message: helpMessage,
          timestamp: new Date().toISOString(),
        },
      ]);
      return 'help_processed';
    }

    return matchedCommand.action;
  };

  // Get filtered command suggestions
  const getCommandSuggestions = (input: string) => {
    if (!input.startsWith('/') || input.includes(' ')) return [];

    const searchTerm = input.toLowerCase();
    return slashCommands.filter(
      (cmd) =>
        cmd.command.startsWith(searchTerm) ||
        cmd.aliases.some((alias) => alias.startsWith(searchTerm))
    );
  };

  // Send chat message with streaming response (SSE)
  const sendChatMessage = async (message: string) => {
    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    // Reset tool tracking
    setActiveTools([]);

    try {
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let accumulatedMessage = '';

      // Read the stream
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        // Decode the chunk
        const chunk = decoder.decode(value, { stream: true });

        // Parse SSE format (data: content\n\n)
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6); // Remove 'data: ' prefix

            // Check for completion or error signals
            if (data === '[DONE]') {
              // Stream complete - finalize the message
              setChatHistory((prev) => [
                ...prev,
                {
                  type: 'ai',
                  message: accumulatedMessage,
                  timestamp: new Date().toISOString(),
                },
              ]);
              setStreamingMessage('');
              setActiveTools([]);
              return;
            }

            if (data.startsWith('[ERROR]')) {
              const errorMessage = data.slice(8); // Remove '[ERROR] ' prefix
              setChatHistory((prev) => [
                ...prev,
                {
                  type: 'ai',
                  message: errorMessage || 'Something went wrong',
                  timestamp: new Date().toISOString(),
                },
              ]);
              setStreamingMessage('');
              setActiveTools([]);
              return;
            }

            // Check for tool events (JSON formatted)
            if (data.startsWith('[TOOL_START]')) {
              const toolName = data.slice(13); // Remove '[TOOL_START] ' prefix
              setActiveTools((prev) => [...prev, toolName]);
              continue;
            }

            if (data.startsWith('[TOOL_END]')) {
              const toolName = data.slice(11); // Remove '[TOOL_END] ' prefix
              setActiveTools((prev) => prev.filter((t) => t !== toolName));
              continue;
            }

            // Accumulate the message and update streaming display
            accumulatedMessage += data;
            setStreamingMessage(accumulatedMessage);
          }
        }
      }

      // If we exit the loop without [DONE], still save what we have
      if (accumulatedMessage) {
        setChatHistory((prev) => [
          ...prev,
          {
            type: 'ai',
            message: accumulatedMessage,
            timestamp: new Date().toISOString(),
          },
        ]);
        setStreamingMessage('');
        setActiveTools([]);
      }
    } catch (error) {
      // Ignore abort errors (user cancelled)
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Request cancelled');
        return;
      }

      console.error('Chat error:', error);
      setStreamingMessage('');
      setActiveTools([]);
      setChatHistory((prev) => [
        ...prev,
        {
          type: 'ai',
          message:
            "Sorry, I'm having trouble connecting to the AI service right now. Please try again later.",
          timestamp: new Date().toISOString(),
        },
      ]);
    }
  };

  const toggleWidget = (widgetName: string) => {
    setCollapsedWidgets((prev) => ({
      ...prev,
      [widgetName]: !prev[widgetName],
    }));
  };

  // Fetch missing data on component mount (server-side data takes priority)
  useEffect(() => {
    const fetchMissingData = async () => {
      // Only fetch data that wasn't loaded server-side
      const needsClientFetch =
        !initialWeather || !initialFinancial || !initialCalendar || !initialTodos;

      if (!needsClientFetch) {
        console.log('✅ Using server-side loaded data, skipping client fetch');
        setLoading(false);
        // Add initial AI greeting
        setChatHistory([
          {
            type: 'ai',
            message:
              "Good morning! I've gathered your daily briefing. Would you like me to explain anything in detail or help you plan your day?",
            timestamp: new Date().toISOString(),
          },
        ]);
        return;
      }

      console.log('🔄 Some data missing from server-side load, fetching client-side...');
      setLoading(true);

      try {
        // Fetch only missing data individually to avoid type issues
        if (!initialWeather) {
          const weatherData = await apiClient.getWeather();
          setWeather(weatherData);
        }

        if (!initialFinancial) {
          const financialData = await apiClient.getFinancialData();
          setFinancial(financialData);
        }

        if (!initialCalendar) {
          const calendarData = await apiClient.getCalendar();
          setCalendar(calendarData);
        }

        if (!initialTodos) {
          const todoData = await apiClient.getTodos(
            selectedBucket === 'all' ? undefined : selectedBucket
          );
          setTodos(todoData);
        }

        // Add initial AI greeting
        setChatHistory([
          {
            type: 'ai',
            message:
              "Good morning! I've gathered your daily briefing. Would you like me to explain anything in detail or help you plan your day?",
            timestamp: new Date().toISOString(),
          },
        ]);
      } catch (error) {
        console.error('Error fetching missing dashboard data:', error);
        // Display server errors if available
        if (serverErrors) {
          console.log('Server-side fetch errors:', serverErrors);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchMissingData();
  }, [
    initialWeather,
    initialFinancial,
    initialCalendar,
    initialTodos,
    serverErrors,
    selectedBucket,
  ]);

  // Refresh todos when bucket selection changes. Goes through the UI proxy
  // (cookie carries auth) — direct browser→Agent calls can't attach the
  // internal auth secret.
  const refreshTodos = async (bucket: TodoBucket | 'all') => {
    try {
      setLoading(true);
      const url = bucket === 'all'
        ? '/api/v1/todos'
        : `/api/v1/todos?bucket=${encodeURIComponent(bucket)}`;
      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`todos ${resp.status}`);
      const todoData = (await resp.json()) as TodoData;
      setTodos(todoData);
    } catch (error) {
      console.error('Error refreshing todos:', error);
    } finally {
      setLoading(false);
    }
  };

  // Handle bucket change
  const handleBucketChange = async (bucket: TodoBucket | 'all') => {
    if (bucket !== selectedBucket) {
      setSelectedBucket(bucket);
      await refreshTodos(bucket);
    }
  };

  const handleSendMessage = async () => {
    if (!chatMessage.trim() || isLoadingChat) return;

    const userInput = chatMessage.trim();
    setChatMessage('');
    setShowCommandSuggestions(false);

    // Check if it's a slash command
    const commandResult = processSlashCommand(userInput);

    if (commandResult === 'help_processed') {
      // Help command was processed locally, no need to send to AI
      return;
    }

    // For slash commands, send the actual command, not the translated action
    const userMessage = userInput; // Always send what the user actually typed
    setIsLoadingChat(true);

    // Add user message to history immediately (show original input, not translated command)
    setChatHistory((prev) => [
      ...prev,
      {
        type: 'user',
        message: userInput,
        timestamp: new Date().toISOString(),
      },
    ]);

    try {
      await sendChatMessage(userMessage);
    } finally {
      setIsLoadingChat(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showCommandSuggestions && chatMessage.startsWith('/') && !chatMessage.includes(' ')) {
      const suggestions = getCommandSuggestions(chatMessage);

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedCommandIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : 0));
        return;
      }

      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedCommandIndex((prev) => (prev > 0 ? prev - 1 : suggestions.length - 1));
        return;
      }

      if (e.key === 'Tab' || (e.key === 'Enter' && suggestions.length > 0)) {
        e.preventDefault();
        const selectedCommand = suggestions[selectedCommandIndex];
        if (selectedCommand) {
          setChatMessage(selectedCommand.command + ' ');
          setShowCommandSuggestions(false);
          setSelectedCommandIndex(0);
        }
        return;
      }

      if (e.key === 'Escape') {
        e.preventDefault();
        setShowCommandSuggestions(false);
        setSelectedCommandIndex(0);
        return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  const allCollapsed = Object.values(collapsedWidgets).every((collapsed) => collapsed);

  return (
    <div className="relative min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      {/* Ambient gradient background */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-20 h-96 w-96 rounded-full bg-indigo-400/10 blur-3xl dark:bg-indigo-600/10" />
        <div className="absolute top-1/2 -right-40 h-[28rem] w-[28rem] rounded-full bg-fuchsia-400/10 blur-3xl dark:bg-fuchsia-600/10" />
        <div className="absolute bottom-0 left-1/3 h-80 w-80 rounded-full bg-cyan-400/10 blur-3xl dark:bg-cyan-600/10" />
      </div>

      {/* Header - Sticky and Mobile Optimized */}
      <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/70 backdrop-blur-xl dark:border-white/10 dark:bg-slate-950/70">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6 sm:py-3.5 lg:px-8">
          {/* Brand */}
          <div className="flex min-w-0 items-center gap-2.5">
            <div className="relative flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 via-fuchsia-500 to-cyan-400 shadow-md shadow-indigo-500/30 sm:h-10 sm:w-10">
              <span className="text-lg" aria-hidden="true">
                ✨
              </span>
              <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-white/20 to-transparent" />
            </div>
            <div className="min-w-0">
              <h1 className="text-base font-semibold tracking-tight text-slate-900 dark:text-white sm:text-lg">
                Aura
              </h1>
              <p className="hidden text-xs text-slate-500 dark:text-slate-400 sm:block">
                Your daily agent
              </p>
            </div>
          </div>

          {/* Clock (center on lg+) */}
          <div className="hidden flex-1 justify-center lg:flex">
            <Clock
              userName={userName}
              className="font-mono text-sm text-slate-600 dark:text-slate-300"
            />
          </div>

          {/* Actions */}
          <div className="flex flex-shrink-0 items-center gap-1.5 sm:gap-2">
            <button
              onClick={() => {
                setCollapsedWidgets({
                  weather: !allCollapsed,
                  financial: !allCollapsed,
                  calendar: !allCollapsed,
                  todos: !allCollapsed,
                  notes: !allCollapsed,
                  habits: !allCollapsed,
                  pomodoro: !allCollapsed,
                  weekendPlanner: !allCollapsed,
                  chat: !allCollapsed,
                });
              }}
              className="hidden items-center gap-1.5 rounded-full border border-slate-200 bg-white/60 px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-white hover:text-slate-900 dark:border-white/10 dark:bg-white/5 dark:text-slate-300 dark:hover:bg-white/10 dark:hover:text-white sm:inline-flex"
              title={allCollapsed ? 'Expand all widgets' : 'Collapse all widgets'}
            >
              <svg
                className={`h-3.5 w-3.5 transition-transform ${allCollapsed ? '' : 'rotate-180'}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
              {allCollapsed ? 'Expand all' : 'Collapse all'}
            </button>

            {/* Dark Mode Toggle */}
            <button
              onClick={toggleDarkMode}
              className="rounded-full border border-slate-200 bg-white/60 p-2 text-slate-600 transition-colors hover:bg-white hover:text-slate-900 dark:border-white/10 dark:bg-white/5 dark:text-slate-300 dark:hover:bg-white/10 dark:hover:text-white"
              aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
              title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {isDark ? (
                <svg className="h-4 w-4 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : (
                <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                </svg>
              )}
            </button>

            {/* User menu / logout — POST form so a cross-origin <img src> can't drive-by log the user out. */}
            <form method="post" action="/auth/logout" className="inline">
              <button
                type="submit"
                title={userEmail ? `Sign out (${userEmail})` : 'Sign out'}
                className="flex items-center gap-2 rounded-full border border-slate-200 bg-white/60 p-1 text-xs font-medium text-slate-700 transition-colors hover:bg-white hover:text-slate-900 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:bg-white/10 dark:hover:text-white sm:pr-3"
                aria-label="Sign out"
              >
                {userPicture ? (
                  <img
                    src={userPicture}
                    alt=""
                    referrerPolicy="no-referrer"
                    className="h-7 w-7 rounded-full ring-2 ring-white dark:ring-slate-800"
                  />
                ) : (
                  <span
                    aria-hidden="true"
                    className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-fuchsia-500 text-xs font-semibold text-white"
                  >
                    {(userName || '?').slice(0, 1).toUpperCase()}
                  </span>
                )}
                <span className="hidden sm:inline">Sign out</span>
              </button>
            </form>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative mx-auto max-w-7xl px-4 pb-24 pt-6 sm:px-6 sm:pt-8 lg:px-8">
        {/* Hero welcome */}
        <section className="mb-8 sm:mb-10">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-widest text-indigo-600 dark:text-indigo-400">
                {new Date().toLocaleDateString(undefined, {
                  weekday: 'long',
                  month: 'long',
                  day: 'numeric',
                })}
              </p>
              <h2 className="mt-2 bg-gradient-to-br from-slate-900 via-slate-700 to-slate-900 bg-clip-text text-3xl font-bold tracking-tight text-transparent dark:from-white dark:via-slate-200 dark:to-white sm:text-4xl">
                {getGreeting()}, {userName}.
              </h2>
              <p className="mt-2 max-w-xl text-sm text-slate-600 dark:text-slate-400 sm:text-base">
                Here's everything that matters today — your calendar, tasks, markets, and weather,
                all in one view. Ask the AI assistant anything below.
              </p>
            </div>

            {/* Stat strip — quick at-a-glance metrics */}
            <div className="grid w-full grid-cols-3 gap-2 sm:gap-3 lg:w-auto lg:flex-shrink-0">
              <div className="rounded-xl border border-slate-200/70 bg-white/60 px-3 py-2.5 backdrop-blur-sm dark:border-white/10 dark:bg-white/[0.04] sm:px-4 sm:py-3">
                <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500 dark:text-slate-400">
                  <span aria-hidden="true">🌤️</span>
                  <span>Weather</span>
                </div>
                <div className="mt-1 text-lg font-semibold text-slate-900 dark:text-white sm:text-xl">
                  {weather ? `${weather.data.current_temp}°` : '—'}
                </div>
              </div>
              <div className="rounded-xl border border-slate-200/70 bg-white/60 px-3 py-2.5 backdrop-blur-sm dark:border-white/10 dark:bg-white/[0.04] sm:px-4 sm:py-3">
                <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500 dark:text-slate-400">
                  <span aria-hidden="true">📅</span>
                  <span>Events</span>
                </div>
                <div className="mt-1 text-lg font-semibold text-slate-900 dark:text-white sm:text-xl">
                  {calendar?.data?.total_events ?? '—'}
                </div>
              </div>
              <div className="rounded-xl border border-slate-200/70 bg-white/60 px-3 py-2.5 backdrop-blur-sm dark:border-white/10 dark:bg-white/[0.04] sm:px-4 sm:py-3">
                <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500 dark:text-slate-400">
                  <span aria-hidden="true">✅</span>
                  <span>Pending</span>
                </div>
                <div className="mt-1 text-lg font-semibold text-slate-900 dark:text-white sm:text-xl">
                  {todos?.data?.pending_count ?? '—'}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION: At a Glance — Weather + Markets */}
        <SectionHeader
          title="At a Glance"
          subtitle="Live data and ambient info"
          tag="Info"
        />
        <div className="mb-8 grid grid-cols-1 gap-3 sm:gap-4 md:grid-cols-2">
          {/* Weather Widget */}
          <div
            className={`${CARD_BASE} ${collapsedWidgets.weather ? 'p-3' : 'p-4 sm:p-6'}`}
          >
            <div
              className={`flex items-center justify-between ${collapsedWidgets.weather ? 'mb-0' : 'mb-4'}`}
            >
              <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900 dark:text-white">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-sky-100 text-base dark:bg-sky-500/20">
                  🌤️
                </span>
                Weather
                {collapsedWidgets.weather && weather && (
                  <span className="ml-1 text-xs font-normal text-slate-500 dark:text-slate-400">
                    {weather.data.current_temp}°F, {weather.data.condition}
                  </span>
                )}
              </h2>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  {weather?.data?.location || 'Loading...'}
                </span>
                <button
                  onClick={() => toggleWidget('weather')}
                  className={CHEVRON_BTN}
                  aria-label={collapsedWidgets.weather ? 'Expand weather' : 'Collapse weather'}
                >
                  <svg
                    className={`h-4 w-4 text-slate-500 transition-transform ${collapsedWidgets.weather ? '' : 'rotate-180'}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>
              </div>
            </div>
            {!collapsedWidgets.weather && (
              <>
                {loading ? (
                  <div className="space-y-3 animate-pulse">
                    <div className="flex items-center justify-between">
                      <div className="h-10 bg-slate-200 dark:bg-white/10 rounded w-20"></div>
                      <div className="h-4 bg-slate-200 dark:bg-white/10 rounded w-24"></div>
                    </div>
                    <div className="h-3 bg-slate-200 dark:bg-white/10 rounded w-full"></div>
                  </div>
                ) : weather ? (
                  <div className="space-y-3">
                    <div className="flex items-end justify-between">
                      <span className="bg-gradient-to-br from-sky-500 to-indigo-500 bg-clip-text text-4xl font-bold text-transparent dark:from-sky-300 dark:to-indigo-300">
                        {weather.data.current_temp}°F
                      </span>
                      <span className="text-sm text-slate-600 dark:text-slate-300">
                        {weather.data.condition}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
                      <span>↑ {weather.data.temp_hi}°F</span>
                      <span>↓ {weather.data.temp_lo}°F</span>
                      <span>💧 {weather.data.precip_chance}%</span>
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-red-500">Failed to load weather data</div>
                )}
              </>
            )}
          </div>

          {/* Financial Widget */}
          <div
            className={`${CARD_BASE} ${collapsedWidgets.financial ? 'p-3' : 'p-4 sm:p-6'}`}
          >
            <div
              className={`flex items-center justify-between ${collapsedWidgets.financial ? 'mb-0' : 'mb-4'}`}
            >
              <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900 dark:text-white">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-100 text-base dark:bg-emerald-500/20">
                  💰
                </span>
                Markets
                {collapsedWidgets.financial && financial?.data?.data && (
                  <span className="ml-1 text-xs font-normal text-slate-500 dark:text-slate-400">
                    {financial.data.data.length} stocks
                  </span>
                )}
              </h2>
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-white/5 dark:text-slate-400">
                  {financial?.data?.market_status || 'Loading...'}
                </span>
                <button
                  onClick={() => toggleWidget('financial')}
                  className={CHEVRON_BTN}
                  aria-label={collapsedWidgets.financial ? 'Expand markets' : 'Collapse markets'}
                >
                  <svg
                    className={`h-4 w-4 transition-transform ${collapsedWidgets.financial ? '' : 'rotate-180'}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>
              </div>
            </div>
            {!collapsedWidgets.financial && (
              <>
                {loading ? (
                  <div className="space-y-2.5 animate-pulse">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="flex justify-between items-center">
                        <div className="h-4 bg-slate-200 dark:bg-white/10 rounded w-12"></div>
                        <div className="text-right space-y-1">
                          <div className="h-4 bg-slate-200 dark:bg-white/10 rounded w-16"></div>
                          <div className="h-3 bg-slate-200 dark:bg-white/10 rounded w-10"></div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : financial?.data?.data ? (
                  <div className="space-y-2.5">
                    {financial.data.data.slice(0, 3).map((item) => (
                      <div
                        key={item.symbol}
                        className="flex items-center justify-between rounded-lg px-1.5 py-1 transition-colors hover:bg-slate-50 dark:hover:bg-white/5"
                      >
                        <span className="font-mono text-sm font-semibold text-slate-700 dark:text-slate-200">
                          {item.symbol}
                        </span>
                        <div className="flex items-baseline gap-2">
                          <span className="text-sm font-bold text-slate-900 dark:text-white">
                            $
                            {item.price.toLocaleString(undefined, {
                              minimumFractionDigits:
                                item.data_type === 'crypto' && item.price > 1000 ? 0 : 2,
                              maximumFractionDigits:
                                item.data_type === 'crypto' && item.price > 1000 ? 0 : 2,
                            })}
                          </span>
                          <span
                            className={`text-xs font-medium ${
                              item.change_percent >= 0
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : 'text-rose-600 dark:text-rose-400'
                            }`}
                          >
                            {item.change_percent >= 0 ? '▲' : '▼'}
                            {Math.abs(item.change_percent).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-red-500">Failed to load financial data</div>
                )}
              </>
            )}
          </div>
        </div>

        {/* SECTION: Today's Focus — Calendar + Tasks */}
        <SectionHeader
          title="Today's Focus"
          subtitle="What's on your plate right now"
          tag="Actionable"
        />
        <div className="mb-8 grid grid-cols-1 gap-3 sm:gap-4 md:grid-cols-2">
          {/* Calendar Widget */}
          <div
            className={`${CARD_BASE} ${collapsedWidgets.calendar ? 'p-3' : 'p-4 sm:p-6'}`}
          >
            <div
              className={`flex items-center justify-between ${collapsedWidgets.calendar ? 'mb-0' : 'mb-4'}`}
            >
              <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900 dark:text-white">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-violet-100 text-base dark:bg-violet-500/20">
                  📅
                </span>
                Today
                {collapsedWidgets.calendar && calendar?.data?.total_events !== undefined && (
                  <span className="ml-1 text-xs font-normal text-slate-500 dark:text-slate-400">
                    {calendar.data.total_events} events
                  </span>
                )}
              </h2>
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-white/5 dark:text-slate-400">
                  {calendar?.data?.total_events !== undefined
                    ? `${calendar.data.total_events} event${calendar.data.total_events === 1 ? '' : 's'}`
                    : 'Loading...'}
                </span>
                <button
                  onClick={() => toggleWidget('calendar')}
                  className={CHEVRON_BTN}
                  aria-label={collapsedWidgets.calendar ? 'Expand calendar' : 'Collapse calendar'}
                >
                  <svg
                    className={`h-4 w-4 transition-transform ${collapsedWidgets.calendar ? '' : 'rotate-180'}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>
              </div>
            </div>
            {!collapsedWidgets.calendar && (
              <>
                {loading ? (
                  <div className="space-y-3 animate-pulse">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="border-l-2 border-slate-200 dark:border-white/10 pl-3">
                        <div className="h-4 bg-slate-200 dark:bg-white/10 rounded w-24 mb-1"></div>
                        <div className="h-3 bg-slate-200 dark:bg-white/10 rounded w-16"></div>
                      </div>
                    ))}
                  </div>
                ) : calendar?.data?.events && calendar.data.events.length > 0 ? (
                  <div className="space-y-2.5">
                    {calendar.data.events.map((event, index) => {
                      const colorMap: Record<string, string> = {
                        blue: 'border-blue-500 bg-blue-50/50 dark:bg-blue-500/5',
                        green: 'border-emerald-500 bg-emerald-50/50 dark:bg-emerald-500/5',
                        orange: 'border-orange-500 bg-orange-50/50 dark:bg-orange-500/5',
                        red: 'border-rose-500 bg-rose-50/50 dark:bg-rose-500/5',
                        purple: 'border-violet-500 bg-violet-50/50 dark:bg-violet-500/5',
                      };
                      const colorClass = event.color
                        ? colorMap[event.color] ||
                          'border-slate-400 bg-slate-50/50 dark:bg-white/[0.02]'
                        : 'border-slate-400 bg-slate-50/50 dark:bg-white/[0.02]';
                      return (
                        <div
                          key={index}
                          className={`rounded-r-lg border-l-2 px-3 py-1.5 ${colorClass}`}
                        >
                          <div className="text-sm font-medium text-slate-900 dark:text-white">
                            {event.title}
                          </div>
                          <div className="text-xs text-slate-500 dark:text-slate-400">
                            {formatEventTime(event)}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : calendar?.data ? (
                  <div className="flex flex-col items-center justify-center py-6 text-center">
                    <span className="text-3xl" aria-hidden="true">
                      🎉
                    </span>
                    <p className="mt-2 text-sm font-medium text-slate-900 dark:text-white">
                      Nothing scheduled
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Your calendar is clear today.
                    </p>
                  </div>
                ) : (
                  <div className="text-sm text-red-500">Failed to load calendar data</div>
                )}
              </>
            )}
          </div>

          {/* Todo Widget */}
          <div
            className={`${CARD_BASE} ${collapsedWidgets.todos ? 'p-3' : 'p-4 sm:p-6'}`}
          >
            <div
              className={`flex items-center justify-between ${collapsedWidgets.todos ? 'mb-0' : 'mb-4'}`}
            >
              <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900 dark:text-white">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-100 text-base dark:bg-emerald-500/20">
                  ✅
                </span>
                Tasks
                {collapsedWidgets.todos && todos?.data?.pending_count !== undefined && (
                  <span className="ml-1 text-xs font-normal text-slate-500 dark:text-slate-400">
                    {todos.data.pending_count} pending
                  </span>
                )}
              </h2>
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-white/5 dark:text-slate-400">
                  {todos?.data?.pending_count !== undefined
                    ? `${todos.data.pending_count} pending`
                    : 'Loading...'}
                </span>
                <button
                  onClick={() => toggleWidget('todos')}
                  className={CHEVRON_BTN}
                  aria-label={collapsedWidgets.todos ? 'Expand tasks' : 'Collapse tasks'}
                >
                  <svg
                    className={`h-4 w-4 transition-transform ${collapsedWidgets.todos ? '' : 'rotate-180'}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>
              </div>
            </div>
            {!collapsedWidgets.todos && (
              <>
                {/* Bucket Selector */}
                <div className="mb-3 flex flex-wrap items-center gap-1.5 border-b border-slate-100 dark:border-white/10 pb-3">
                  {(['all', 'work', 'home', 'errands', 'personal'] as const).map((bucket) => (
                    <button
                      key={bucket}
                      onClick={() => handleBucketChange(bucket)}
                      className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
                        selectedBucket === bucket
                          ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-500/30'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-white/5 dark:text-slate-300 dark:hover:bg-white/10'
                      }`}
                    >
                      {bucket === 'all'
                        ? 'All'
                        : bucket.charAt(0).toUpperCase() + bucket.slice(1)}
                    </button>
                  ))}
                  <button
                    onClick={() => handleBucketChange('all')}
                    className="ml-auto text-xs font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
                  >
                    Refresh
                  </button>
                </div>

                {loading ? (
                  <div className="space-y-2 animate-pulse">
                    {[1, 2, 3, 4].map((i) => (
                      <div key={i} className="flex items-center gap-2">
                        <div className="h-4 w-4 bg-slate-200 dark:bg-white/10 rounded"></div>
                        <div className="h-4 bg-slate-200 dark:bg-white/10 rounded flex-1"></div>
                      </div>
                    ))}
                  </div>
                ) : todos?.data?.items && todos.data.items.length > 0 ? (
                  <div className="space-y-1">
                    {todos.data.items.slice(0, 4).map((item) => {
                      const isCompleted = todoCompletions[item.id] ?? item.completed;
                      return (
                        <label
                          key={item.id}
                          className="flex cursor-pointer items-center gap-2 rounded-lg px-1.5 py-1.5 transition-colors hover:bg-slate-50 dark:hover:bg-white/5"
                        >
                          <input
                            type="checkbox"
                            className="h-4 w-4 cursor-pointer rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 dark:border-white/20 dark:bg-white/5"
                            checked={isCompleted}
                            onChange={() => handleTodoToggle(item.id, isCompleted)}
                          />
                          <span
                            className={`flex-1 text-sm ${isCompleted ? 'line-through text-slate-400 dark:text-slate-500' : 'text-slate-700 dark:text-slate-200'}`}
                          >
                            {item.title}
                          </span>
                          {item.priority === 'high' && (
                            <span className="rounded-full bg-rose-100 px-1.5 py-0.5 text-xs font-bold text-rose-700 dark:bg-rose-500/20 dark:text-rose-300">
                              !
                            </span>
                          )}
                        </label>
                      );
                    })}
                  </div>
                ) : todos?.data ? (
                  <div className="flex flex-col items-center justify-center py-6 text-center">
                    <span className="text-3xl" aria-hidden="true">
                      ✨
                    </span>
                    <p className="mt-2 text-sm font-medium text-slate-900 dark:text-white">
                      All clear!
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      No pending tasks in this bucket.
                    </p>
                  </div>
                ) : (
                  <div className="text-sm text-red-500">Failed to load todo data</div>
                )}
              </>
            )}
          </div>
        </div>

        {/* SECTION: Productivity Tools — Notes, Habits, Pomodoro */}
        <SectionHeader
          title="Productivity Tools"
          subtitle="Capture thoughts, build habits, focus deeply"
          tag="Personal"
        />
        <div className="mb-8 grid grid-cols-1 gap-3 sm:gap-4 md:grid-cols-2 lg:grid-cols-3">
          {/* Notes Widget */}
          <NotesWidget
            collapsed={collapsedWidgets.notes}
            onToggle={() => setCollapsedWidgets((prev) => ({ ...prev, notes: !prev.notes }))}
          />

          {/* Habits Widget */}
          <HabitsWidget
            collapsed={collapsedWidgets.habits}
            onToggle={() => setCollapsedWidgets((prev) => ({ ...prev, habits: !prev.habits }))}
          />

          {/* Pomodoro Widget */}
          <PomodoroWidget
            collapsed={collapsedWidgets.pomodoro}
            onToggle={() => setCollapsedWidgets((prev) => ({ ...prev, pomodoro: !prev.pomodoro }))}
          />
        </div>

        {/* SECTION: Plan Your Weekend */}
        <SectionHeader
          title="Plan Your Weekend"
          subtitle="Ideas powered by your interests"
          tag="Inspire"
        />
        <div className="mb-8">
          {/* Weekend Planner — quick-prompt buttons that drop a message into chat.
              Settings opens as a modal via the gear icon in the header. */}
          <WeekendPlannerWidget
            collapsed={collapsedWidgets.weekendPlanner}
            onToggle={() =>
              setCollapsedWidgets((prev) => ({ ...prev, weekendPlanner: !prev.weekendPlanner }))
            }
            onQuickPrompt={(prompt) => {
              setChatMessage(prompt);
              // Open the chat panel on mobile so the user sees the prefilled message.
              if (collapsedWidgets.chat) {
                setCollapsedWidgets((prev) => ({ ...prev, chat: false }));
              }
            }}
            onOpenSettings={() => setWeekendSettingsOpen(true)}
            preferencesVersion={weekendPrefsVersion}
          />
        </div>

        {/* SECTION: Commute */}
        <SectionHeader
          title="Commute"
          subtitle="Real-time traffic and transit options"
          tag="Live"
        />
        <div className="mb-6">
          <CommuteDashboard />
        </div>

        {/* Weekend Settings modal — opened from the WeekendPlannerWidget gear button */}
        <WeekendSettings
          isOpen={weekendSettingsOpen}
          onClose={() => setWeekendSettingsOpen(false)}
          onPreferencesChanged={() => setWeekendPrefsVersion((v) => v + 1)}
        />

        {/* Mobile Chat Overlay - Creates depth effect behind chat */}
        {!collapsedWidgets.chat && (
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 lg:hidden transition-all duration-300 ease-in-out"
            onClick={() => setCollapsedWidgets((prev) => ({ ...prev, chat: true }))}
            aria-label="Close chat overlay"
          />
        )}

        {/* AI Chat Interface - Bottom Anchored */}
        <div className="fixed bottom-0 left-0 right-0 z-50 border-t border-slate-200/70 bg-white/90 shadow-[0_-8px_32px_rgba(15,23,42,0.08)] backdrop-blur-xl transition-all duration-300 ease-in-out dark:border-white/10 dark:bg-slate-950/90 dark:shadow-[0_-8px_32px_rgba(0,0,0,0.5)] lg:rounded-t-none rounded-t-2xl">
          <div className="max-w-7xl mx-auto">
            <div
              className={`flex flex-col transition-all duration-300 ease-in-out ${collapsedWidgets.chat ? 'h-auto' : 'max-h-[calc(100vh-120px)] lg:max-h-[calc(100vh-200px)] min-h-[200px]'}`}
            >
              {/* Collapsible Header */}
              <div
                className="flex-shrink-0 cursor-pointer border-b border-slate-200/70 p-3 transition-colors duration-200 hover:bg-slate-50 dark:border-white/10 dark:hover:bg-white/[0.03]"
                onClick={() => setCollapsedWidgets((prev) => ({ ...prev, chat: !prev.chat }))}
              >
                {/* Mobile drag handle */}
                <div className="flex justify-center mb-2 lg:hidden">
                  <div className="h-1 w-10 rounded-full bg-slate-300 dark:bg-white/20"></div>
                </div>
                <div className="flex items-center justify-between">
                  <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
                    <span className="flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br from-indigo-500 to-fuchsia-500 text-xs shadow-sm shadow-indigo-500/30">
                      🤖
                    </span>
                    AI Assistant
                    {/* Connection status indicator */}
                    <span
                      className={`h-2 w-2 rounded-full ${
                        agentStatus === 'online'
                          ? 'bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.6)]'
                          : agentStatus === 'offline'
                            ? 'bg-rose-500'
                            : 'animate-pulse bg-amber-500'
                      }`}
                      title={`Agent ${agentStatus}`}
                    />
                  </h2>
                  <div className="flex items-center space-x-2">
                    {chatHistory.length > 1 && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleClearChatHistory();
                        }}
                        className="text-xs text-gray-500 hover:text-red-500 dark:text-gray-400 dark:hover:text-red-400 transition-colors"
                        title="Clear chat history"
                      >
                        Clear
                      </button>
                    )}
                    <svg
                      className={`w-4 h-4 text-gray-500 transition-transform duration-300 ease-in-out ${collapsedWidgets.chat ? 'rotate-180' : ''}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </div>
                </div>
              </div>
              {/* Messages Area - Only show when not collapsed */}
              <div
                className={`flex flex-col flex-1 min-h-0 transition-all duration-300 ease-in-out overflow-hidden ${collapsedWidgets.chat ? 'max-h-0 opacity-0' : 'max-h-[calc(100vh-200px)] lg:max-h-[calc(100vh-280px)] opacity-100'}`}
              >
                <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-3 space-y-2">
                  {/* Show existing messages first */}
                  {chatHistory.map((message, index) => (
                    <div
                      key={index}
                      className={`${
                        message.type === 'user'
                          ? 'ml-6 bg-gradient-to-br from-indigo-500 to-fuchsia-500 text-white shadow-md shadow-indigo-500/20'
                          : 'mr-6 bg-slate-100 text-slate-900 dark:bg-white/[0.06] dark:text-slate-100'
                      } rounded-2xl px-3.5 py-2.5 text-sm`}
                    >
                      {message.type === 'user' && message.message.startsWith('/') ? (
                        // Special rendering for slash commands
                        <div>
                          {(() => {
                            const messageText = message.message;
                            const spaceIndex = messageText.indexOf(' ');

                            if (spaceIndex === -1) {
                              // Just the command, no additional text
                              return (
                                <span className="rounded bg-white/20 px-1.5 py-0.5 font-mono font-semibold text-white">
                                  {messageText}
                                </span>
                              );
                            } else {
                              // Command + additional text
                              const command = messageText.substring(0, spaceIndex);
                              const rest = messageText.substring(spaceIndex);
                              return (
                                <>
                                  <span className="rounded bg-white/20 px-1.5 py-0.5 font-mono font-semibold text-white">
                                    {command}
                                  </span>
                                  <span className="ml-1 text-white/90">{rest}</span>
                                </>
                              );
                            }
                          })()}
                        </div>
                      ) : (
                        // Regular markdown rendering for non-slash-command messages
                        <ReactMarkdown
                          components={MARKDOWN_COMPONENTS}
                          remarkPlugins={REMARK_PLUGINS}
                        >
                          {normalizeMarkdown(message.message)}
                        </ReactMarkdown>
                      )}
                    </div>
                  ))}

                  {/* Streaming message or loading indicator */}
                  {isLoadingChat && (
                    <div className="mr-6 rounded-2xl bg-slate-100 px-3.5 py-2.5 text-sm dark:bg-white/[0.06]">
                      {/* Show active tools */}
                      {activeTools.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-2">
                          {activeTools.map((tool) => (
                            <span
                              key={tool}
                              className="inline-flex items-center gap-1.5 rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300"
                            >
                              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-500" />
                              {tool.replace(/_/g, ' ')}
                            </span>
                          ))}
                        </div>
                      )}
                      {streamingMessage ? (
                        <ReactMarkdown
                          components={MARKDOWN_COMPONENTS}
                          remarkPlugins={REMARK_PLUGINS}
                        >
                          {normalizeMarkdown(streamingMessage)}
                        </ReactMarkdown>
                      ) : (
                        <span className="text-gray-600 dark:text-gray-300 animate-pulse">
                          {activeTools.length > 0
                            ? `Using ${activeTools[activeTools.length - 1].replace(/_/g, ' ')}...`
                            : 'AI is thinking...'}
                        </span>
                      )}
                      {/* Blinking cursor for streaming effect */}
                      {streamingMessage && (
                        <span className="inline-block w-2 h-4 ml-1 bg-gray-600 dark:bg-gray-300 animate-pulse" />
                      )}
                    </div>
                  )}

                  {/* Show prompts if there are 1 or fewer messages (just initial greeting or empty) */}
                  {chatHistory.length <= 1 && (
                    <div className="p-3 space-y-4">
                      {chatHistory.length === 0 && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
                          Start a conversation with your AI assistant...
                        </div>
                      )}

                      {/* Quick Prompt Buttons */}
                      <div className="grid grid-cols-1 gap-2">
                        {[
                          { text: '/summary', icon: '📊', isCommand: true },
                          { text: '/weather', icon: '🌤️', isCommand: true },
                          { text: '/finance', icon: '💰', isCommand: true },
                          { text: 'How does my day look?', icon: '📅' },
                          { text: 'What tasks do I have today?', icon: '✅' },
                          { text: '/help', icon: '❓', isCommand: true },
                        ].map((prompt, index) => (
                          <button
                            key={index}
                            onClick={async () => {
                              if (isLoadingChat) return;

                              const userMessage = prompt.text;
                              setIsLoadingChat(true);

                              // Add user message to history immediately
                              setChatHistory((prev) => [
                                ...prev,
                                {
                                  type: 'user',
                                  message: userMessage,
                                  timestamp: new Date().toISOString(),
                                },
                              ]);

                              try {
                                await sendChatMessage(userMessage);
                              } finally {
                                setIsLoadingChat(false);
                              }
                            }}
                            disabled={isLoadingChat}
                            className={`flex items-center space-x-2 p-3 text-sm text-left rounded-lg border transition-colors duration-200 group disabled:opacity-50 disabled:cursor-not-allowed ${
                              prompt.isCommand
                                ? 'bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/20 dark:hover:bg-blue-900/30 border-blue-200 dark:border-blue-800'
                                : 'bg-gray-50 hover:bg-gray-100 dark:bg-gray-700 dark:hover:bg-gray-600 border-gray-200 dark:border-gray-600'
                            }`}
                          >
                            <span className="text-base">
                              {isLoadingChat ? (
                                <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
                              ) : (
                                prompt.icon
                              )}
                            </span>
                            <div className="flex items-center justify-between flex-1">
                              <span
                                className={`${
                                  prompt.isCommand
                                    ? 'text-blue-700 dark:text-blue-300 group-hover:text-blue-900 dark:group-hover:text-blue-100'
                                    : 'text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white'
                                }`}
                              >
                                {prompt.text}
                              </span>
                              {prompt.isCommand && (
                                <span className="text-xs text-blue-500 dark:text-blue-400 font-mono">
                                  CMD
                                </span>
                              )}
                            </div>
                          </button>
                        ))}
                      </div>

                      <div className="text-xs text-gray-400 dark:text-gray-500 text-center">
                        Try slash commands above, or type your own message below
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Input Area - Always visible */}
              <div className="relative border-t border-slate-200/70 bg-white/80 p-3 dark:border-white/10 dark:bg-slate-950/60">
                {/* Command Suggestions - Floating above input */}
                {showCommandSuggestions &&
                  chatMessage.startsWith('/') &&
                  !chatMessage.includes(' ') && (
                    <div className="absolute bottom-full left-0 right-0 mb-1 z-10">
                      <div className="mx-3 bg-gray-50/95 dark:bg-gray-900/95 backdrop-blur-sm border border-gray-200/60 dark:border-gray-700/60 rounded-lg shadow-lg">
                        <div className="px-3 py-1 border-b border-gray-200/60 dark:border-gray-700/60">
                          <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center justify-between">
                            <span>Commands</span>
                            <span>↑↓ navigate • ↵ select • esc close</span>
                          </div>
                        </div>
                        <div className="p-2 space-y-1 max-h-48 overflow-y-auto">
                          {getCommandSuggestions(chatMessage).map((cmd, index) => (
                            <button
                              key={index}
                              onClick={() => {
                                setChatMessage(cmd.command + ' ');
                                setShowCommandSuggestions(false);
                                setSelectedCommandIndex(0);
                              }}
                              className={`w-full flex items-center space-x-2 p-2 text-left rounded-md transition-colors text-sm group ${
                                index === selectedCommandIndex
                                  ? 'bg-blue-100/80 dark:bg-blue-900/50 text-blue-900 dark:text-blue-100'
                                  : 'hover:bg-gray-100/80 dark:hover:bg-gray-700/80'
                              }`}
                            >
                              <span className="text-sm">{cmd.icon}</span>
                              <div className="flex-1 min-w-0">
                                <div className="font-medium text-gray-900 dark:text-white text-sm">
                                  {cmd.command}
                                  {cmd.aliases.length > 0 && (
                                    <span className="text-gray-500 dark:text-gray-400 font-normal text-xs ml-1">
                                      ({cmd.aliases.join(', ')})
                                    </span>
                                  )}
                                </div>
                                <div className="text-gray-500 dark:text-gray-400 text-xs truncate">
                                  {cmd.description}
                                </div>
                              </div>
                              <div className="text-xs text-gray-400 dark:text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity">
                                ↵
                              </div>
                            </button>
                          ))}
                          {getCommandSuggestions(chatMessage).length === 0 && (
                            <div className="text-xs text-gray-500 dark:text-gray-400 text-center py-3">
                              No commands found. Try{' '}
                              <code className="bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded text-xs">
                                /help
                              </code>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                <div className="flex space-x-2">
                  <input
                    type="text"
                    placeholder="Type your message or / for commands..."
                    value={chatMessage}
                    onChange={(e) => {
                      const value = e.target.value;
                      setChatMessage(value);

                      // Show command suggestions only when actively typing a command (no space yet)
                      if (value.startsWith('/') && value.length > 0 && !value.includes(' ')) {
                        setShowCommandSuggestions(true);
                        setSelectedCommandIndex(0); // Reset selection
                      } else {
                        setShowCommandSuggestions(false);
                        setSelectedCommandIndex(0);
                      }
                    }}
                    onKeyDown={handleKeyDown}
                    disabled={isLoadingChat}
                    className={`flex-1 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 transition-all focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 disabled:opacity-50 dark:border-white/10 dark:bg-white/[0.04] dark:text-white dark:placeholder:text-slate-500 ${
                      chatMessage.startsWith('/')
                        ? 'border-indigo-300 bg-indigo-50/50 font-medium text-indigo-600 dark:border-indigo-500/40 dark:bg-indigo-500/10 dark:text-indigo-200'
                        : ''
                    }`}
                    autoComplete="off"
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={isLoadingChat || !chatMessage.trim()}
                    className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-gradient-to-br from-indigo-500 to-fuchsia-500 px-4 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-500/30 transition-all hover:shadow-lg hover:shadow-indigo-500/40 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
                  >
                    {isLoadingChat ? (
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    ) : (
                      'Send'
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
