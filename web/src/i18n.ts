/**
 * Arabic / English switch. Arabic is the default; the choice is remembered on
 * this device. Strings are written in place as tr(arabic, english) so each
 * translation sits next to the text it translates.
 */
import { useSyncExternalStore } from 'react';

export type Lang = 'ar' | 'en';

const STORAGE_KEY = 'homerehab-lang';
const listeners = new Set<() => void>();

function storedLang(): Lang {
  try {
    return globalThis.localStorage?.getItem(STORAGE_KEY) === 'en' ? 'en' : 'ar';
  } catch {
    return 'ar';
  }
}

let current: Lang = storedLang();

function applyToDocument(): void {
  if (typeof document !== 'undefined') {
    document.documentElement.lang = current;
    document.documentElement.dir = current === 'ar' ? 'rtl' : 'ltr';
  }
}
applyToDocument();

export function getLang(): Lang {
  return current;
}

export function setLang(lang: Lang): void {
  current = lang;
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, lang);
  } catch {
    // remembering the choice is optional
  }
  applyToDocument();
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Re-renders the caller when the language changes. */
export function useLang(): Lang {
  return useSyncExternalStore(subscribe, getLang, getLang);
}

/** The string for the current language. */
export function tr(ar: string, en: string): string {
  return current === 'en' ? en : ar;
}
