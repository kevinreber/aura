import { useEffect, useState } from 'react';

interface CatalogCategory {
  id: string;
  label: string;
  description: string;
  default_enabled: boolean;
  tools: string[];
}

interface WeekendPreferences {
  enabled_categories: string[];
  pinned_artists: string[];
  excluded_artists: string[];
  activity_preferences: string[];
  max_drive_hours: number;
  budget_level: string;
  home_base: string | null;
}

interface WeekendPlannerWidgetProps {
  collapsed?: boolean;
  onToggle?: () => void;
  /** Called when a quick-prompt button is clicked. Parent (Dashboard) is
   * responsible for sending the message into the chat input. */
  onQuickPrompt?: (message: string) => void;
  /** Called when the gear button in the header is clicked. Parent should
   * open the WeekendSettings modal. */
  onOpenSettings?: () => void;
  /** Bumped by the parent whenever prefs change so the widget refetches.
   * Any value change triggers a reload. */
  preferencesVersion?: number;
}

const CATEGORY_ICONS: Record<string, string> = {
  trails: '🥾',
  concerts: '🎵',
  itinerary: '🗺️',
};

// Quick-prompt templates per category. The widget fills in the user's
// home_base when one is configured; otherwise prompts use a generic placeholder.
function buildPrompts(category: CatalogCategory, homeBase: string | null): string[] {
  const where = homeBase || 'my area';
  switch (category.id) {
    case 'trails':
      return [
        `Find me hiking trails near ${where}`,
        `What's a good easy trail under 5 miles near ${where}?`,
        `Suggest a moderate hike near ${where} for this weekend`,
      ];
    case 'concerts':
      return [
        `What concerts are happening in ${where} this weekend?`,
        `Any live music in ${where} in the next two weeks?`,
        `Find concerts near ${where} for my favorite artists`,
      ];
    case 'itinerary':
      return [
        `Plan a 2-day trip to ${where} with food and outdoors`,
        `Suggest a weekend itinerary for ${where}`,
        `What should I do for a long weekend somewhere within 4 hours of ${where}?`,
      ];
    default:
      return [`Tell me about ${category.label.toLowerCase()} in ${where}`];
  }
}

export function WeekendPlannerWidget({
  collapsed = false,
  onToggle,
  onQuickPrompt,
  onOpenSettings,
  preferencesVersion = 0,
}: WeekendPlannerWidgetProps) {
  const [preferences, setPreferences] = useState<WeekendPreferences | null>(null);
  const [catalog, setCatalog] = useState<CatalogCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetch('/api/v1/preferences');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        setPreferences(data.preferences);
        setCatalog(data.catalog);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : 'Failed to load preferences');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
    // Re-fetch when the parent signals prefs changed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preferencesVersion]);

  const enabledCategories = preferences?.enabled_categories ?? [];
  const enabledCatalog = catalog.filter((c) => enabledCategories.includes(c.id));
  const homeBase = preferences?.home_base ?? null;

  return (
    <div
      className={`group rounded-2xl border border-slate-200/70 bg-white/80 shadow-sm shadow-slate-200/40 backdrop-blur-sm transition-all hover:border-slate-300 hover:shadow-md dark:border-white/10 dark:bg-white/[0.04] dark:shadow-none dark:hover:border-white/20 ${collapsed ? 'p-3' : 'p-4 sm:p-6'}`}
    >
      <div className={`flex items-center justify-between ${collapsed ? 'mb-0' : 'mb-4'}`}>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
          🌤️ Weekend Planner
          {collapsed && enabledCategories.length > 0 && (
            <span className="ml-2 text-sm font-normal text-gray-600 dark:text-gray-400">
              {enabledCategories.length} active
            </span>
          )}
        </h2>
        <div className="flex items-center space-x-1">
          <button
            onClick={onOpenSettings}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors text-gray-500 dark:text-gray-400"
            aria-label="Open weekend settings"
            title="Weekend settings"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          </button>
          <button
            onClick={onToggle}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            aria-label={collapsed ? 'Expand weekend planner' : 'Collapse weekend planner'}
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
      </div>

      {!collapsed && (
        <div className="space-y-3">
          {loading && (
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
              Loading preferences…
            </p>
          )}

          {error && (
            <p className="text-sm text-red-600 dark:text-red-400 text-center py-2">
              {error}
            </p>
          )}

          {!loading && !error && enabledCatalog.length === 0 && (
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
              All weekend categories are disabled. Enable them in Weekend Settings to
              see suggestions here.
            </p>
          )}

          {!loading && enabledCatalog.length > 0 && (
            <div className="space-y-3">
              {enabledCatalog.map((category) => {
                const prompts = buildPrompts(category, homeBase);
                return (
                  <div
                    key={category.id}
                    className="p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50"
                  >
                    <div className="flex items-center mb-2">
                      <span className="text-lg mr-2">
                        {CATEGORY_ICONS[category.id] || '📍'}
                      </span>
                      <div>
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {category.label}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {category.description}
                        </div>
                      </div>
                    </div>
                    <div className="space-y-1.5">
                      {prompts.map((prompt) => (
                        <button
                          key={prompt}
                          onClick={() => onQuickPrompt?.(prompt)}
                          className="w-full text-left text-xs px-2.5 py-1.5 rounded-md bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 dark:hover:border-blue-500 transition-colors text-gray-700 dark:text-gray-300"
                        >
                          {prompt}
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
              <p className="text-xs text-gray-500 dark:text-gray-400 text-center pt-1">
                Tap a prompt to send it to chat
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
