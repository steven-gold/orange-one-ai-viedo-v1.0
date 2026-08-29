"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  isLocale,
  LOCALE_HTML_LANG,
  type Locale,
  type TranslationKey,
  translate,
} from "./catalog";

type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: TranslationKey) => string;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);
const STORAGE_KEY = "acpos.locale";

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("zh-TW");

  useEffect(() => {
    const persisted = window.localStorage.getItem(STORAGE_KEY);
    if (isLocale(persisted)) setLocaleState(persisted);
  }, []);

  useEffect(() => {
    document.documentElement.lang = LOCALE_HTML_LANG[locale];
  }, [locale]);

  const setLocale = (nextLocale: Locale) => {
    setLocaleState(nextLocale);
    window.localStorage.setItem(STORAGE_KEY, nextLocale);
  };

  const value = useMemo<LocaleContextValue>(
    () => ({ locale, setLocale, t: (key) => translate(locale, key) }),
    [locale],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useI18n(): LocaleContextValue {
  const context = useContext(LocaleContext);
  if (!context) throw new Error("useI18n must be used within LocaleProvider");
  return context;
}
