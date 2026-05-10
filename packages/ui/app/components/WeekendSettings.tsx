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

interface WeekendSettingsProps {
  /** Whether the modal is currently visible. */
  isOpen: boolean;
  /** Called when the user wants to dismiss the modal — backdrop click, X, or Escape. */
  onClose: () => void;
  /** Called when prefs are saved successfully so the parent can refresh
   * other widgets (like WeekendPlannerWidget) that depend on prefs. */
  onPreferencesChanged?: () => void;
}

const CATEGORY_ICONS: Record<string, string> = {
  trails: '🥾',
  concerts: '🎵',
  itinerary: '🗺️',
};

export function WeekendSettings({
  isOpen,
  onClose,
  onPreferencesChanged,
}: WeekendSettingsProps) {
  const [preferences, setPreferences] = useState<WeekendPreferences | null>(null);
  const [catalog, setCatalog] = useState<CatalogCategory[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<Date | null>(null);

  // Escape key closes the modal.
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  // Load prefs each time the modal opens so toggles reflect any external edits.
  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
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
  }, [isOpen]);

  async function toggleCategory(categoryId: string) {
    if (!preferences) return;

    const current = preferences.enabled_categories;
    const next = current.includes(categoryId)
      ? current.filter((c) => c !== categoryId)
      : [...current, categoryId];

    const updated: WeekendPreferences = {
      ...preferences,
      enabled_categories: next,
    };

    // Optimistic update so the toggle feels instant.
    const previous = preferences;
    setPreferences(updated);
    setSaving(true);
    setError(null);

    try {
      const res = await fetch('/api/v1/preferences', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated),
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.error || `HTTP ${res.status}`);
      }
      setSavedAt(new Date());
      onPreferencesChanged?.();
    } catch (e) {
      // Roll back on failure.
      setPreferences(previous);
      setError(e instanceof Error ? e.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  }

  if (!isOpen) return null;

  const enabled = new Set(preferences?.enabled_categories ?? []);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="weekend-settings-title"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm transition-opacity" />

      {/* Modal card */}
      <div
        className="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 w-full max-w-md max-h-[85vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 sm:p-6 border-b border-gray-200 dark:border-gray-700">
          <h2
            id="weekend-settings-title"
            className="text-lg font-semibold text-gray-900 dark:text-white flex items-center"
          >
            ⚙️ Weekend Settings
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors text-gray-500 dark:text-gray-400"
            aria-label="Close settings"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="p-4 sm:p-6 space-y-3">
          {loading && (
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
              Loading…
            </p>
          )}

          {error && (
            <p className="text-sm text-red-600 dark:text-red-400 py-2 px-3 bg-red-50 dark:bg-red-900/20 rounded-md">
              {error}
            </p>
          )}

          {!loading && catalog.length > 0 && (
            <>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Toggle which weekend categories the agent should consider when planning.
                Changes apply immediately to your next chat message.
              </p>

              <div className="space-y-2">
                {catalog.map((category) => {
                  const isEnabled = enabled.has(category.id);
                  return (
                    <div
                      key={category.id}
                      className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50"
                    >
                      <div className="flex items-center min-w-0 mr-3">
                        <span className="text-lg mr-2 flex-shrink-0">
                          {CATEGORY_ICONS[category.id] || '📍'}
                        </span>
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-gray-900 dark:text-white truncate">
                            {category.label}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                            {category.description}
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => toggleCategory(category.id)}
                        disabled={saving}
                        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-wait ${
                          isEnabled
                            ? 'bg-blue-600'
                            : 'bg-gray-300 dark:bg-gray-600'
                        }`}
                        aria-label={`${isEnabled ? 'Disable' : 'Enable'} ${category.label}`}
                        aria-pressed={isEnabled}
                      >
                        <span
                          className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow ring-0 transition-transform duration-200 ease-in-out ${
                            isEnabled ? 'translate-x-5' : 'translate-x-0'
                          }`}
                        />
                      </button>
                    </div>
                  );
                })}
              </div>

              {savedAt && !error && (
                <p className="text-xs text-green-600 dark:text-green-400 text-center pt-1">
                  ✓ Saved {savedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
