import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { useDarkMode } from '../hooks/useDarkMode';
import { usePolling } from '../hooks/usePolling';
import {
  apiClient,
  type CalendarData,
  type CommuteOptionsData,
  type FinancialData,
  type TodoData,
  type TomorrowBriefing,
  type WeatherData,
} from '../lib/api';
import {
  clearChatHistory,
  getCachedData,
  loadChatHistory,
  loadTodoCompletions,
  saveChatHistory,
  setCachedData,
  toggleTodoCompletion,
} from '../lib/storage';
import { AuraShell } from './aura/AuraShell';
import {
  adaptCommute,
  adaptEvents,
  adaptMarkets,
  adaptTodos,
  adaptTomorrow,
  adaptWeather,
  MOCK_HABITS,
  MOCK_NOTES,
} from './aura/types';

interface DashboardProps {
  userName?: string;
  userEmail?: string;
  userPicture?: string;
  initialWeather?: WeatherData | null;
  initialFinancial?: FinancialData | null;
  initialCalendar?: CalendarData | null;
  initialTodos?: TodoData | null;
  initialCommute?: CommuteOptionsData | null;
  initialTomorrow?: TomorrowBriefing | null;
  serverErrors?: {
    weather?: string | null;
    financial?: string | null;
    calendar?: string | null;
    todos?: string | null;
    commute?: string | null;
    tomorrow?: string | null;
  };
}

interface SlashCommand {
  command: string;
  aliases: string[];
  description: string;
  icon: string;
  action: string;
}

const SLASH_COMMANDS: SlashCommand[] = [
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
    description: 'Show your task list',
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
    action: 'help',
  },
];

function buildHelpMessage(): string {
  return `**Available Slash Commands:**\n\n${SLASH_COMMANDS.filter((c) => c.action !== 'help')
    .map(
      (c) =>
        `${c.icon} **${c.command}** ${c.aliases.length ? `(${c.aliases.join(', ')})` : ''}\n${c.description}`
    )
    .join('\n\n')}`;
}

function resolveSlashCommand(input: string): SlashCommand | null {
  const trimmed = input.trim();
  if (!trimmed.startsWith('/')) return null;
  const head = trimmed.split(' ')[0].toLowerCase();
  return SLASH_COMMANDS.find((c) => c.command === head || c.aliases.includes(head)) ?? null;
}

// POST to /auth/logout so a drive-by GET can't sign the user out.
function submitLogout() {
  const form = document.createElement('form');
  form.method = 'POST';
  form.action = '/auth/logout';
  document.body.appendChild(form);
  form.submit();
}

export default function Dashboard({
  userName = 'Kevin',
  userEmail,
  initialWeather,
  initialFinancial,
  initialCalendar,
  initialTodos,
  initialCommute,
  initialTomorrow,
}: DashboardProps) {
  const [weather] = useState<WeatherData | null>(initialWeather ?? null);
  const [financial, setFinancial] = useState<FinancialData | null>(initialFinancial ?? null);
  const [calendar, setCalendar] = useState<CalendarData | null>(initialCalendar ?? null);
  const [todos, setTodos] = useState<TodoData | null>(initialTodos ?? null);
  const [commute] = useState<CommuteOptionsData | null>(initialCommute ?? null);
  const [tomorrow] = useState<TomorrowBriefing | null>(initialTomorrow ?? null);

  const [chatHistory, setChatHistory] = useState<
    Array<{ type: 'user' | 'ai'; message: string; timestamp: string }>
  >(() => loadChatHistory());
  const [todoCompletions, setTodoCompletions] = useState<Record<string, boolean>>(() =>
    loadTodoCompletions()
  );
  const [isLoadingChat, setIsLoadingChat] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState<string>('');

  const abortControllerRef = useRef<AbortController | null>(null);
  const { theme, toggle: toggleDarkMode } = useDarkMode();

  // Polled financial data — proxy through the UI server so the session
  // cookie carries auth (browser→Agent calls can't attach the secret).
  const fetchFinancialData = useCallback(async () => {
    const cached = getCachedData<FinancialData>('financial');
    if (cached) return cached;
    const resp = await fetch('/api/v1/financial', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbols: ['MSFT', 'BTC', 'ETH', 'NVDA'], data_type: 'mixed' }),
    });
    if (!resp.ok) throw new Error(`financial ${resp.status}`);
    const data = (await resp.json()) as FinancialData;
    setCachedData('financial', data, 5 * 60 * 1000);
    return data;
  }, []);

  const { data: polledFinancial } = usePolling({
    fetcher: fetchFinancialData,
    interval: 5 * 60 * 1000,
    enabled: !!initialFinancial,
  });

  useEffect(() => {
    if (polledFinancial) setFinancial(polledFinancial);
  }, [polledFinancial]);

  // Persist chat history.
  useEffect(() => {
    if (chatHistory.length > 0) saveChatHistory(chatHistory);
  }, [chatHistory]);

  // Initial AI greeting once data is loaded, if the user has no prior history.
  useEffect(() => {
    if (chatHistory.length === 0) {
      setChatHistory([
        {
          type: 'ai',
          message: `Morning, ${userName}. I've gathered your daily briefing — where do you want to start?`,
          timestamp: new Date().toISOString(),
        },
      ]);
    }
    // run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fill in any data missing from server-side load.
  useEffect(() => {
    const missing = !initialWeather || !initialFinancial || !initialCalendar || !initialTodos;
    if (!missing) return;
    (async () => {
      try {
        if (!initialFinancial) setFinancial(await apiClient.getFinancialData());
        if (!initialCalendar) setCalendar(await apiClient.getCalendar());
        if (!initialTodos) setTodos(await apiClient.getTodos());
      } catch (err) {
        console.error('Error fetching missing dashboard data:', err);
      }
    })();
  }, [initialWeather, initialFinancial, initialCalendar, initialTodos]);

  // SSE chat stream — same wire format as before. Reads `data: …` frames,
  // dispatches [TOOL_START]/[TOOL_END]/[ERROR]/[DONE] control messages.
  const sendChatMessage = async (message: string) => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
        signal: abortControllerRef.current.signal,
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let accumulated = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split('\n')) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6);

          if (data === '[DONE]') {
            setChatHistory((prev) => [
              ...prev,
              { type: 'ai', message: accumulated, timestamp: new Date().toISOString() },
            ]);
            setStreamingMessage('');
            return;
          }
          if (data.startsWith('[ERROR]')) {
            setChatHistory((prev) => [
              ...prev,
              {
                type: 'ai',
                message: data.slice(8) || 'Something went wrong',
                timestamp: new Date().toISOString(),
              },
            ]);
            setStreamingMessage('');
            return;
          }
          if (data.startsWith('[TOOL_START]') || data.startsWith('[TOOL_END]')) continue;
          accumulated += data;
          setStreamingMessage(accumulated);
        }
      }

      if (accumulated) {
        setChatHistory((prev) => [
          ...prev,
          { type: 'ai', message: accumulated, timestamp: new Date().toISOString() },
        ]);
        setStreamingMessage('');
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') return;
      console.error('Chat error:', error);
      setStreamingMessage('');
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

  // onSend: translate slash commands, handle /help locally, push the user
  // message into history, then stream the agent's reply.
  const handleSend = async (raw: string) => {
    const text = raw.trim();
    if (!text || isLoadingChat) return;

    const matched = resolveSlashCommand(text);
    if (matched?.action === 'help') {
      setChatHistory((prev) => [
        ...prev,
        { type: 'user', message: text, timestamp: new Date().toISOString() },
        { type: 'ai', message: buildHelpMessage(), timestamp: new Date().toISOString() },
      ]);
      return;
    }

    const outbound = matched?.action ?? text;
    setIsLoadingChat(true);
    setChatHistory((prev) => [
      ...prev,
      { type: 'user', message: text, timestamp: new Date().toISOString() },
    ]);
    try {
      await sendChatMessage(outbound);
    } finally {
      setIsLoadingChat(false);
    }
  };

  const handleClearChat = () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    clearChatHistory();
    setStreamingMessage('');
    setIsLoadingChat(false);
    setChatHistory([
      {
        type: 'ai',
        message: 'Chat history cleared. How can I help you today?',
        timestamp: new Date().toISOString(),
      },
    ]);
  };

  const handleToggleTodo = (id: string) => {
    const current = todoCompletions[id] ?? false;
    const updated = toggleTodoCompletion(id, !current);
    setTodoCompletions(updated);
  };

  // Map server payloads → view-models.
  const weatherVM = useMemo(() => adaptWeather(weather), [weather]);
  const marketsVM = useMemo(() => adaptMarkets(financial), [financial]);
  const eventsVM = useMemo(() => adaptEvents(calendar), [calendar]);
  const tasksVM = useMemo(() => adaptTodos(todos, todoCompletions), [todos, todoCompletions]);
  const tomorrowVM = useMemo(() => adaptTomorrow(tomorrow), [tomorrow]);
  const commuteVM = useMemo(() => adaptCommute(commute), [commute]);

  return (
    <AuraShell
      userName={userName}
      userEmail={userEmail}
      weather={weatherVM}
      markets={marketsVM}
      events={eventsVM}
      tasks={tasksVM}
      tomorrow={tomorrowVM}
      commute={commuteVM}
      habits={MOCK_HABITS}
      notes={MOCK_NOTES}
      onToggleTodo={handleToggleTodo}
      messages={chatHistory}
      streaming={streamingMessage}
      isLoadingChat={isLoadingChat}
      onSend={handleSend}
      onClearChat={handleClearChat}
      theme={theme}
      onToggleTheme={toggleDarkMode}
      onSignOut={submitLogout}
    />
  );
}
