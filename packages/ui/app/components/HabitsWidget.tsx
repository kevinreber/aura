import { useEffect, useState } from 'react';
import {
  getHabitStreak,
  type Habit,
  type HabitLog,
  loadHabitLogs,
  loadHabits,
  saveHabitLogs,
  saveHabits,
} from '../lib/storage';

interface HabitsWidgetProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

const HABIT_ICONS = ['💪', '📚', '🧘', '💧', '🏃', '🎯', '✍️', '🌱', '😴', '🥗'];

export function HabitsWidget({ collapsed = false, onToggle }: HabitsWidgetProps) {
  const [habits, setHabits] = useState<Habit[]>([]);
  const [habitLogs, setHabitLogs] = useState<HabitLog[]>([]);
  const [newHabitName, setNewHabitName] = useState('');
  const [selectedIcon, setSelectedIcon] = useState(HABIT_ICONS[0]);
  const [showAddForm, setShowAddForm] = useState(false);

  const today = new Date().toISOString().split('T')[0];

  useEffect(() => {
    setHabits(loadHabits());
    setHabitLogs(loadHabitLogs());
  }, []);

  const handleAddHabit = () => {
    if (!newHabitName.trim()) return;

    const newHabit: Habit = {
      id: Date.now().toString(),
      name: newHabitName.trim(),
      icon: selectedIcon,
      createdAt: new Date().toISOString(),
    };

    const updatedHabits = [...habits, newHabit];
    setHabits(updatedHabits);
    saveHabits(updatedHabits);
    setNewHabitName('');
    setShowAddForm(false);
  };

  const handleDeleteHabit = (id: string) => {
    const updatedHabits = habits.filter((h) => h.id !== id);
    const updatedLogs = habitLogs.filter((l) => l.habitId !== id);
    setHabits(updatedHabits);
    setHabitLogs(updatedLogs);
    saveHabits(updatedHabits);
    saveHabitLogs(updatedLogs);
  };

  const toggleHabitCompletion = (habitId: string) => {
    const existingLog = habitLogs.find((l) => l.habitId === habitId && l.date === today);

    let updatedLogs: HabitLog[];
    if (existingLog) {
      updatedLogs = habitLogs.map((l) =>
        l.habitId === habitId && l.date === today ? { ...l, completed: !l.completed } : l
      );
    } else {
      updatedLogs = [...habitLogs, { habitId, date: today, completed: true }];
    }

    setHabitLogs(updatedLogs);
    saveHabitLogs(updatedLogs);
  };

  const isCompletedToday = (habitId: string): boolean => {
    const log = habitLogs.find((l) => l.habitId === habitId && l.date === today);
    return log?.completed ?? false;
  };

  const completedCount = habits.filter((h) => isCompletedToday(h.id)).length;

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 transition-all ${collapsed ? 'p-3' : 'p-4 sm:p-6'}`}
    >
      <div className={`flex items-center justify-between ${collapsed ? 'mb-0' : 'mb-4'}`}>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
          🎯 Habits
          {collapsed && habits.length > 0 && (
            <span className="ml-2 text-sm font-normal text-gray-600 dark:text-gray-400">
              {completedCount}/{habits.length} today
            </span>
          )}
        </h2>
        <button
          onClick={onToggle}
          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
          aria-label={collapsed ? 'Expand habits' : 'Collapse habits'}
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
      </div>

      {!collapsed && (
        <div className="space-y-3">
          {/* Progress Bar */}
          {habits.length > 0 && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                <span>Today's Progress</span>
                <span>
                  {completedCount}/{habits.length}
                </span>
              </div>
              <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-500 transition-all duration-300"
                  style={{ width: `${(completedCount / habits.length) * 100}%` }}
                />
              </div>
            </div>
          )}

          {/* Habits List */}
          <div className="space-y-2">
            {habits.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                No habits yet. Add one to start tracking!
              </p>
            ) : (
              habits.map((habit) => {
                const streak = getHabitStreak(habit.id, habitLogs);
                const completed = isCompletedToday(habit.id);

                return (
                  <div
                    key={habit.id}
                    className={`flex items-center justify-between p-2 rounded-lg transition-colors group ${
                      completed
                        ? 'bg-green-50 dark:bg-green-900/20'
                        : 'bg-gray-50 dark:bg-gray-700/50'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <button
                        onClick={() => toggleHabitCompletion(habit.id)}
                        className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors ${
                          completed
                            ? 'bg-green-500 border-green-500 text-white'
                            : 'border-gray-300 dark:border-gray-600 hover:border-green-400'
                        }`}
                      >
                        {completed && (
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path
                              fillRule="evenodd"
                              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                              clipRule="evenodd"
                            />
                          </svg>
                        )}
                      </button>
                      <span className="text-lg">{habit.icon}</span>
                      <span
                        className={`text-sm ${completed ? 'line-through text-gray-400' : 'text-gray-700 dark:text-gray-300'}`}
                      >
                        {habit.name}
                      </span>
                    </div>
                    <div className="flex items-center space-x-2">
                      {streak > 0 && (
                        <span className="text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 px-2 py-0.5 rounded-full">
                          🔥 {streak} day{streak !== 1 ? 's' : ''}
                        </span>
                      )}
                      <button
                        onClick={() => handleDeleteHabit(habit.id)}
                        className="opacity-0 group-hover:opacity-100 text-red-500 hover:text-red-600 transition-opacity"
                        title="Delete habit"
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path
                            fillRule="evenodd"
                            d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Add Habit Form */}
          {showAddForm ? (
            <div className="space-y-2 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <input
                type="text"
                value={newHabitName}
                onChange={(e) => setNewHabitName(e.target.value)}
                placeholder="Habit name..."
                className="w-full px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-1 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                onKeyDown={(e) => e.key === 'Enter' && handleAddHabit()}
              />
              <div className="flex items-center space-x-2">
                <span className="text-xs text-gray-500 dark:text-gray-400">Icon:</span>
                <div className="flex flex-wrap gap-1">
                  {HABIT_ICONS.map((icon) => (
                    <button
                      key={icon}
                      onClick={() => setSelectedIcon(icon)}
                      className={`w-7 h-7 rounded flex items-center justify-center text-sm transition-colors ${
                        selectedIcon === icon
                          ? 'bg-blue-100 dark:bg-blue-900/50'
                          : 'hover:bg-gray-100 dark:hover:bg-gray-600'
                      }`}
                    >
                      {icon}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={handleAddHabit}
                  disabled={!newHabitName.trim()}
                  className="flex-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Add
                </button>
                <button
                  onClick={() => {
                    setShowAddForm(false);
                    setNewHabitName('');
                  }}
                  className="px-3 py-1.5 text-sm bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-500"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowAddForm(true)}
              className="w-full px-3 py-1.5 text-sm border border-dashed border-gray-300 dark:border-gray-600 text-gray-500 dark:text-gray-400 rounded-lg hover:border-blue-400 hover:text-blue-600 dark:hover:border-blue-500 dark:hover:text-blue-400 transition-colors"
            >
              + Add Habit
            </button>
          )}
        </div>
      )}
    </div>
  );
}
