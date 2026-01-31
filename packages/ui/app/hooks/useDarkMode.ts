import { useEffect, useState } from 'react';
import { loadDarkMode, saveDarkMode } from '../lib/storage';

export function useDarkMode() {
  const [isDark, setIsDark] = useState<boolean>(() => {
    // Initialize from localStorage or system preference
    if (typeof window === 'undefined') return false;
    return loadDarkMode() ?? false;
  });

  useEffect(() => {
    // Apply dark mode class on mount and changes
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    saveDarkMode(isDark);
  }, [isDark]);

  const toggle = () => setIsDark((prev) => !prev);

  return { isDark, setIsDark, toggle };
}
