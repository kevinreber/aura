import { useCallback, useEffect, useRef, useState } from 'react';
import {
  DEFAULT_POMODORO_SETTINGS,
  loadPomodoroSettings,
  type PomodoroSettings,
  savePomodoroSettings,
} from '../lib/storage';

interface PomodoroWidgetProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

type TimerState = 'idle' | 'work' | 'break' | 'longBreak';

export function PomodoroWidget({ collapsed = false, onToggle }: PomodoroWidgetProps) {
  const [settings, setSettings] = useState<PomodoroSettings>(DEFAULT_POMODORO_SETTINGS);
  const [timerState, setTimerState] = useState<TimerState>('idle');
  const [timeLeft, setTimeLeft] = useState(0);
  const [sessionsCompleted, setSessionsCompleted] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    setSettings(loadPomodoroSettings());
    // Create audio element for notification
    if (typeof window !== 'undefined') {
      audioRef.current = new Audio(
        'data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdH2Onp+fn5yXkYd6cmZgXV9kbXiEj5qgoaKhn5mSi4J5cGlkYmRpcHeEkJuipKSlop+ZkYmAd29pZWRlaW94hZCboquur62qpZ6WjIN7c2xnZWZqcXqGkZyksLKysK2nn5aNg3pxamZkZmtweoeSmae0tbWzr6qjm5GHfXRsZ2VmbHJ7iJSfqbi5ubazraaglo2CeHBqZmZrb3qGkp2pubq6uLSvqaKYjYN5cGplZWpwd4SQnKe3urq4tbCqo5qPg3pxamZmam53g4+bqLm8vbu4s62mnpWKgHdvamZnam94hI+dqry+vr26trCqo5qQhXx0bWhnbHJ6hpKfq77AwL67t7GspaGWi4F5cWpmZ2xzeYWRnqu/wcHAvrq0r6ijmY6EenJrZ2dscXmFkZ6rwMPDwb68trGspaGXjYN6cmxoaGxyd4ORnqvBxMXDwb26tbCro5mOhHpzbWlobnN6hpKfrcPGxsXCv7q1sKukmI6DenRuamhscnqGkqCuxsnJx8XCvri0r6qjl4uBeXJtaWltdHqHk6GwycvLycfDwLm1sKukmY+Ee3VwamhscnqGk6KyzM3OzcrIw7+5tbGspZqQhnx1cGtnbHJ7hpWkttDR0dDOy8fCvbm0sKukmJCEe3Vva2htc3yIl6a61NPU09HOy8fCvri0sKukmZGFfHVwa2htdH2JmKi91dbW1dLPy8fCvbi0sKyllpKGfHZxa2ltdH2Jmai91tbX1tTRzcnFwb24tLCopZmTiX95dHBtbHF5goqYqLvW19jX1dLOy8jEwL25tbKvq6WalIt/d3JtamxxeICHlKS109fY2NbU0c7KxsLAu7m1sa6rqKKXjYN4c25qanB3foWRoLPS19jY19bU0c3Lx8TAvby5trSxrqqmmJKJgXh0b2tscHd+hI+etdPX2NnY19XT0c7Lx8TBv7y6uLa0sq+rqaWfmJCJgXp1cW5sc3l/hY6cudTX2NnZ2NfV09DPzMnHxMK/vbq4trSyr6yqqKWhnpmTjYV+eHRwbnJ2fYOLlqnH1tfY2dnY19XT0tDOzMrIxsO/vry6uLazsK6sq6impKKfm5eUj4qEfnl1cnF0eX6Ei5Wmy9fY2dnZ2NjX1dTT0dDOzcvIxsO/vry6uLa0sq+trKqpp6SjopycmZWRjYmFgHt3dHN1eX2CiJCetNPX2NnZ2dnY19bV1NPR0M7NysjGw8C+vLq4trSysa6trKupp6eloqGgn5ual5SRjYqHg4B8eXZ0dHZ6fYKHjpqsydXX2NnZ2dnY19bV1NPR0M7My8nHxcLAvry6uLe1s7GwrqyqqaelpaOhoqCfnZyal5SRjYqHhIF/fHl3dnd5fH+Eh4yVpLzS1tfY2dnZ2djX1tXU0tHPzszKyMbDwb+9u7m3trSysK6trKqoqKalpqSjo6Kgn5ybl5WSkI2KiIaEgX99e3l4eHl7fYCDhoyUoLLK1NbX2NnZ2djY19bV1NLR0M7My8nHxcPBv728urm3trSwrq2sq6mop6alpKOioaCfnpyamJaUkpCOjIqIhoSCgH59e3p5eXp7fYCChIiOlqO0y9TV1tfY2djY19bV1NPR0M7NzMrIxsTCwL68u7m4trW0srCvrayrqqmop6alpKOioaGfnpycmpqYlpSSkI6Mi4mHhYOBgH59fHt6ent8fX+Bg4aJjpSfrMLQ1NXW19jY2NfW1dTT0dDPzszLycfFw8G/vry7ubm3trSzsrCuraysqqmoqKenpaSkoqGgn56dnJuamJeVlJKQj42LiomHhYSDgYCAf358fHx9foCChIaIi4+VobPG0NTU1dfX19fX1tXU09LQ0M7NzMrJx8XDwcC+vbu6ubm3trSzsa+uram='
      );
    }
  }, []);

  const playNotification = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.play().catch(() => {
        // Audio play failed, likely due to autoplay restrictions
      });
    }
    // Also try to show browser notification
    if ('Notification' in window && Notification.permission === 'granted') {
      const messages: Record<TimerState, string> = {
        idle: '',
        work: 'Time to take a break!',
        break: 'Break over! Time to focus.',
        longBreak: 'Long break over! Ready for a new session?',
      };
      new Notification('Pomodoro Timer', { body: messages[timerState] });
    }
  }, [timerState]);

  const startTimer = useCallback(
    (state: TimerState) => {
      const durations: Record<TimerState, number> = {
        idle: 0,
        work: settings.workDuration * 60,
        break: settings.breakDuration * 60,
        longBreak: settings.longBreakDuration * 60,
      };
      setTimerState(state);
      setTimeLeft(durations[state]);
      setIsRunning(true);
    },
    [settings]
  );

  const stopTimer = () => {
    setIsRunning(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  const resetTimer = () => {
    stopTimer();
    setTimerState('idle');
    setTimeLeft(0);
    setSessionsCompleted(0);
  };

  useEffect(() => {
    if (isRunning && timeLeft > 0) {
      intervalRef.current = setInterval(() => {
        setTimeLeft((prev) => prev - 1);
      }, 1000);
    } else if (timeLeft === 0 && isRunning) {
      playNotification();
      stopTimer();

      // Auto-transition to next phase
      if (timerState === 'work') {
        const newSessionsCompleted = sessionsCompleted + 1;
        setSessionsCompleted(newSessionsCompleted);

        if (newSessionsCompleted % settings.sessionsBeforeLongBreak === 0) {
          startTimer('longBreak');
        } else {
          startTimer('break');
        }
      } else if (timerState === 'break' || timerState === 'longBreak') {
        setTimerState('idle');
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isRunning, timeLeft, timerState, sessionsCompleted, settings, playNotification, startTimer]);

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSettingChange = (key: keyof PomodoroSettings, value: number) => {
    const newSettings = { ...settings, [key]: value };
    setSettings(newSettings);
    savePomodoroSettings(newSettings);
  };

  const getStateColor = () => {
    switch (timerState) {
      case 'work':
        return 'text-red-500';
      case 'break':
        return 'text-green-500';
      case 'longBreak':
        return 'text-blue-500';
      default:
        return 'text-gray-500';
    }
  };

  const getStateLabel = () => {
    switch (timerState) {
      case 'work':
        return 'Focus Time';
      case 'break':
        return 'Short Break';
      case 'longBreak':
        return 'Long Break';
      default:
        return 'Ready';
    }
  };

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 transition-all ${collapsed ? 'p-3' : 'p-4 sm:p-6'}`}
    >
      <div className={`flex items-center justify-between ${collapsed ? 'mb-0' : 'mb-4'}`}>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
          🍅 Pomodoro
          {collapsed && timerState !== 'idle' && (
            <span className={`ml-2 text-sm font-mono ${getStateColor()}`}>
              {formatTime(timeLeft)}
            </span>
          )}
        </h2>
        <div className="flex items-center space-x-2">
          {!collapsed && (
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
              title="Settings"
            >
              <svg className="w-4 h-4 text-gray-500" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          )}
          <button
            onClick={onToggle}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            aria-label={collapsed ? 'Expand pomodoro' : 'Collapse pomodoro'}
          >
            <svg
              className={`w-4 h-4 text-gray-500 transition-transform ${collapsed ? '' : 'rotate-180'}`}
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

      {!collapsed && (
        <div className="space-y-4">
          {showSettings ? (
            <div className="space-y-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">Settings</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs text-gray-600 dark:text-gray-400">Work (min)</label>
                  <input
                    type="number"
                    min="1"
                    max="60"
                    value={settings.workDuration}
                    onChange={(e) => handleSettingChange('workDuration', parseInt(e.target.value))}
                    className="w-16 px-2 py-1 text-sm border border-gray-200 dark:border-gray-600 rounded dark:bg-gray-700 dark:text-white"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-xs text-gray-600 dark:text-gray-400">Break (min)</label>
                  <input
                    type="number"
                    min="1"
                    max="30"
                    value={settings.breakDuration}
                    onChange={(e) => handleSettingChange('breakDuration', parseInt(e.target.value))}
                    className="w-16 px-2 py-1 text-sm border border-gray-200 dark:border-gray-600 rounded dark:bg-gray-700 dark:text-white"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-xs text-gray-600 dark:text-gray-400">
                    Long Break (min)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="60"
                    value={settings.longBreakDuration}
                    onChange={(e) =>
                      handleSettingChange('longBreakDuration', parseInt(e.target.value))
                    }
                    className="w-16 px-2 py-1 text-sm border border-gray-200 dark:border-gray-600 rounded dark:bg-gray-700 dark:text-white"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-xs text-gray-600 dark:text-gray-400">
                    Sessions before long break
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={settings.sessionsBeforeLongBreak}
                    onChange={(e) =>
                      handleSettingChange('sessionsBeforeLongBreak', parseInt(e.target.value))
                    }
                    className="w-16 px-2 py-1 text-sm border border-gray-200 dark:border-gray-600 rounded dark:bg-gray-700 dark:text-white"
                  />
                </div>
              </div>
              <button
                onClick={() => setShowSettings(false)}
                className="w-full px-3 py-1.5 text-sm bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-500"
              >
                Done
              </button>
            </div>
          ) : (
            <>
              {/* Timer Display */}
              <div className="text-center">
                <div className={`text-4xl font-mono font-bold ${getStateColor()}`}>
                  {timerState === 'idle'
                    ? formatTime(settings.workDuration * 60)
                    : formatTime(timeLeft)}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  {getStateLabel()}
                </div>
                <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                  Sessions: {sessionsCompleted}
                </div>
              </div>

              {/* Controls */}
              <div className="flex justify-center space-x-2">
                {timerState === 'idle' ? (
                  <button
                    onClick={() => startTimer('work')}
                    className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors font-medium"
                  >
                    Start Focus
                  </button>
                ) : (
                  <>
                    <button
                      onClick={() => setIsRunning(!isRunning)}
                      className={`px-4 py-2 rounded-lg transition-colors font-medium ${
                        isRunning
                          ? 'bg-yellow-500 hover:bg-yellow-600 text-white'
                          : 'bg-green-500 hover:bg-green-600 text-white'
                      }`}
                    >
                      {isRunning ? 'Pause' : 'Resume'}
                    </button>
                    <button
                      onClick={resetTimer}
                      className="px-4 py-2 bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-500 transition-colors"
                    >
                      Reset
                    </button>
                  </>
                )}
              </div>

              {/* Quick Actions */}
              {timerState === 'idle' && (
                <div className="flex justify-center space-x-2">
                  <button
                    onClick={() => startTimer('break')}
                    className="px-3 py-1 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-lg hover:bg-green-200 dark:hover:bg-green-900/50 transition-colors"
                  >
                    Short Break
                  </button>
                  <button
                    onClick={() => startTimer('longBreak')}
                    className="px-3 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
                  >
                    Long Break
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
