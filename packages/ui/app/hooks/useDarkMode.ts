import { useEffect, useState } from 'react';

// Aura theme hook — drives the design-system `data-theme` attribute on
// <html>. The pre-paint script in root.tsx sets the same attribute from
// `localStorage['aura-theme']` so there's no flash on first paint.
const STORAGE_KEY = 'aura-theme';

function readInitial(): 'dark' | 'light' {
  if (typeof window === 'undefined') return 'dark';
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === 'dark' || stored === 'light') return stored;
  const attr = document.documentElement.getAttribute('data-theme');
  return attr === 'light' ? 'light' : 'dark';
}

export function useDarkMode() {
  const [theme, setTheme] = useState<'dark' | 'light'>(readInitial);

  useEffect(() => {
    const el = document.documentElement;
    // Suppress transitions during the switch — see aura.css `.theme-switching`.
    el.classList.add('theme-switching');
    el.setAttribute('data-theme', theme);
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // ignore quota / private-mode failures
    }
    const id = requestAnimationFrame(() =>
      requestAnimationFrame(() => el.classList.remove('theme-switching'))
    );
    return () => cancelAnimationFrame(id);
  }, [theme]);

  const toggle = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'));

  return { theme, isDark: theme === 'dark', setTheme, toggle };
}
