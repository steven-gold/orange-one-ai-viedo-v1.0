"use client";

import { useCallback } from "react";
import type { FocusEvent } from "react";

export interface KeyboardNav {
  onSidebarFocus: () => void;
  onSidebarBlur: (event: FocusEvent<HTMLElement>) => void;
}

export function useKeyboardNav(expand: () => void): KeyboardNav {
  const onSidebarFocus = useCallback(() => {
    expand();
  }, [expand]);

  const onSidebarBlur = useCallback((event: FocusEvent<HTMLElement>) => {
    const next = event.relatedTarget as Node | null;
    if (next && event.currentTarget.contains(next)) return;
  }, []);

  return { onSidebarFocus, onSidebarBlur };
}
