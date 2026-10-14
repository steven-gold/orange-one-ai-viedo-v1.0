"use client";

import type { ReactNode } from "react";

export type IconName =
  | "play"
  | "pause"
  | "prev"
  | "next"
  | "stop"
  | "fullscreen"
  | "volume"
  | "mute"
  | "loop"
  | "rate"
  | "single"
  | "compare"
  | "send"
  | "undo"
  | "redo"
  | "select"
  | "razor"
  | "split"
  | "trim-start"
  | "trim-end"
  | "move"
  | "reorder"
  | "delete"
  | "duplicate"
  | "transition"
  | "speed"
  | "replace"
  | "clip-volume"
  | "fade"
  | "fade-in"
  | "fade-out"
  | "upload"
  | "audition"
  | "zoom-in"
  | "zoom-out"
  | "fit"
  | "marker"
  | "snap"
  | "lock"
  | "solo"
  | "visible"
  | "subtitle"
  | "set-in"
  | "set-out"
  | "clear"
  | "range"
  | "single-ai"
  | "multi-ai"
  | "blueprint"
  | "package"
  | "manifest"
  | "back"
  | "attachment"
  | "reference"
  | "record";

type IconNode = { body: ReactNode; fill?: boolean };

const ICONS: Record<IconName, IconNode> = {
  play: { body: <polygon points="6 3 20 12 6 21 6 3" />, fill: true },
  pause: {
    body: (
      <>
        <rect x="6" y="4" width="4" height="16" rx="1" />
        <rect x="14" y="4" width="4" height="16" rx="1" />
      </>
    ),
    fill: true,
  },
  prev: {
    body: (
      <>
        <polygon points="19 20 9 12 19 4 19 20" fill="currentColor" stroke="none" />
        <line x1="5" x2="5" y1="19" y2="5" />
      </>
    ),
  },
  next: {
    body: (
      <>
        <polygon points="5 4 15 12 5 20 5 4" fill="currentColor" stroke="none" />
        <line x1="19" x2="19" y1="5" y2="19" />
      </>
    ),
  },
  stop: { body: <rect x="6" y="6" width="12" height="12" rx="1" />, fill: true },
  fullscreen: {
    body: (
      <>
        <path d="M8 3H5a2 2 0 0 0-2 2v3" />
        <path d="M21 8V5a2 2 0 0 0-2-2h-3" />
        <path d="M3 16v3a2 2 0 0 0 2 2h3" />
        <path d="M16 21h3a2 2 0 0 0 2-2v-3" />
      </>
    ),
  },
  volume: {
    body: (
      <>
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
        <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
        <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
      </>
    ),
  },
  mute: {
    body: (
      <>
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
        <line x1="22" x2="16" y1="9" y2="15" />
        <line x1="16" x2="22" y1="9" y2="15" />
      </>
    ),
  },
  loop: {
    body: (
      <>
        <path d="m17 2 4 4-4 4" />
        <path d="M3 11v-1a4 4 0 0 1 4-4h14" />
        <path d="m7 22-4-4 4-4" />
        <path d="M21 13v1a4 4 0 0 1-4 4H3" />
      </>
    ),
  },
  rate: {
    body: (
      <>
        <path d="m12 14 4-4" />
        <path d="M3.34 19a10 10 0 1 1 17.32 0" />
      </>
    ),
  },
  single: {
    body: (
      <>
        <rect width="18" height="18" x="3" y="3" rx="2" />
        <circle cx="12" cy="12" r="3" />
      </>
    ),
  },
  compare: {
    body: (
      <>
        <rect width="18" height="18" x="3" y="3" rx="2" />
        <path d="M12 3v18" />
        <path d="m8 9-2 3 2 3" />
        <path d="m16 9 2 3-2 3" />
      </>
    ),
  },
  send: {
    body: (
      <>
        <path d="m22 2-7 20-4-9-9-4Z" />
        <path d="M22 2 11 13" />
      </>
    ),
  },
  undo: {
    body: (
      <>
        <path d="M3 7v6h6" />
        <path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13" />
      </>
    ),
  },
  redo: {
    body: (
      <>
        <path d="M21 7v6h-6" />
        <path d="M3 17a9 9 0 0 1 9-9 9 9 0 0 1 6 2.3L21 13" />
      </>
    ),
  },
  select: { body: <path d="m3 3 7.07 16.97 2.51-7.39 7.39-2.51L3 3z" />, fill: true },
  razor: {
    body: (
      <>
        <circle cx="6" cy="6" r="3" />
        <path d="M8.12 8.12 12 12" />
        <path d="M20 4 8.12 15.88" />
        <circle cx="6" cy="18" r="3" />
        <path d="M14.8 14.8 20 20" />
      </>
    ),
  },
  split: {
    body: (
      <>
        <rect width="18" height="18" x="3" y="3" rx="2" />
        <path d="M12 3v18" />
        <path d="M12 8h-2a2 2 0 0 0-2 2v4a2 2 0 0 0 2 2h2" />
        <path d="M12 8h2a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-2" />
      </>
    ),
  },
  "trim-start": {
    body: (
      <>
        <rect width="18" height="18" x="3" y="3" rx="2" />
        <path d="M9 3v18" />
      </>
    ),
  },
  "trim-end": {
    body: (
      <>
        <rect width="18" height="18" x="3" y="3" rx="2" />
        <path d="M15 3v18" />
      </>
    ),
  },
  move: {
    body: (
      <>
        <polyline points="5 9 2 12 5 15" />
        <polyline points="9 5 12 2 15 5" />
        <polyline points="15 19 12 22 9 19" />
        <polyline points="19 9 22 12 19 15" />
        <line x1="2" x2="22" y1="12" y2="12" />
        <line x1="12" x2="12" y1="2" y2="22" />
      </>
    ),
  },
  reorder: {
    body: (
      <>
        <path d="m3 16 4 4 4-4" />
        <path d="M7 20V4" />
        <path d="m21 8-4-4-4 4" />
        <path d="M17 4v16" />
      </>
    ),
  },
  delete: {
    body: (
      <>
        <path d="M3 6h18" />
        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
        <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      </>
    ),
  },
  duplicate: {
    body: (
      <>
        <rect width="14" height="14" x="8" y="8" rx="2" />
        <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
      </>
    ),
  },
  transition: {
    body: (
      <>
        <rect x="2" y="8" width="8" height="8" rx="1" />
        <rect x="14" y="8" width="8" height="8" rx="1" />
        <path d="M10 12h4" />
      </>
    ),
  },
  speed: {
    body: (
      <>
        <path d="m12 14 4-4" />
        <path d="M3.34 19a10 10 0 1 1 17.32 0" />
      </>
    ),
  },
  replace: {
    body: (
      <>
        <path d="m16 3 4 4-4 4" />
        <path d="M20 7H4" />
        <path d="m8 21-4-4 4-4" />
        <path d="M4 17h16" />
      </>
    ),
  },
  "clip-volume": {
    body: (
      <>
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
        <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
      </>
    ),
  },
  fade: {
    body: (
      <>
        <path d="M3 20 21 4" />
        <path d="M3 20h18" />
        <path d="M3 4v16" />
      </>
    ),
  },
  "fade-in": {
    body: (
      <>
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <path d="M3 20 21 4" />
      </>
    ),
  },
  "fade-out": {
    body: (
      <>
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <path d="M3 4 21 20" />
      </>
    ),
  },
  upload: {
    body: (
      <>
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="17 8 12 3 7 8" />
        <line x1="12" x2="12" y1="3" y2="15" />
      </>
    ),
  },
  audition: {
    body: (
      <path d="M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3" />
    ),
  },
  "zoom-in": {
    body: (
      <>
        <circle cx="11" cy="11" r="8" />
        <line x1="21" x2="16.65" y1="21" y2="16.65" />
        <line x1="11" x2="11" y1="8" y2="14" />
        <line x1="8" x2="14" y1="11" y2="11" />
      </>
    ),
  },
  "zoom-out": {
    body: (
      <>
        <circle cx="11" cy="11" r="8" />
        <line x1="21" x2="16.65" y1="21" y2="16.65" />
        <line x1="8" x2="14" y1="11" y2="11" />
      </>
    ),
  },
  fit: {
    body: (
      <>
        <path d="M8 3H5a2 2 0 0 0-2 2v3" />
        <path d="M21 8V5a2 2 0 0 0-2-2h-3" />
        <path d="M3 16v3a2 2 0 0 0 2 2h3" />
        <path d="M16 21h3a2 2 0 0 0 2-2v-3" />
      </>
    ),
  },
  marker: {
    body: (
      <>
        <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
        <line x1="4" x2="4" y1="22" y2="15" />
      </>
    ),
  },
  snap: {
    body: (
      <>
        <path d="m6 15-4-4 6.75-6.77a7.79 7.79 0 0 1 11 11L13 22l-4-4 6.39-6.36a2.14 2.14 0 0 0-3-3L6 15" />
        <path d="m5 8 4 4" />
        <path d="m12 15 4 4" />
      </>
    ),
  },
  lock: {
    body: (
      <>
        <rect width="18" height="11" x="3" y="11" rx="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </>
    ),
  },
  solo: {
    body: (
      <>
        <path d="M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3" />
      </>
    ),
  },
  visible: {
    body: (
      <>
        <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
        <circle cx="12" cy="12" r="3" />
      </>
    ),
  },
  subtitle: {
    body: (
      <>
        <rect width="20" height="14" x="2" y="5" rx="2" />
        <path d="M7 15h4" />
        <path d="M15 15h2" />
        <path d="M7 11h2" />
        <path d="M13 11h4" />
      </>
    ),
  },
  "set-in": {
    body: (
      <>
        <path d="M6 3v18" />
        <path d="M11 8h9" />
        <path d="M11 16h9" />
      </>
    ),
  },
  "set-out": {
    body: (
      <>
        <path d="M18 3v18" />
        <path d="M4 8h9" />
        <path d="M4 16h9" />
      </>
    ),
  },
  clear: {
    body: (
      <>
        <path d="M18 6 6 18" />
        <path d="m6 6 12 12" />
      </>
    ),
  },
  range: {
    body: (
      <>
        <path d="M8 3v18" />
        <path d="M16 3v18" />
        <path d="M8 12h8" />
      </>
    ),
  },
  "single-ai": {
    body: (
      <>
        <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </>
    ),
  },
  "multi-ai": {
    body: (
      <>
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </>
    ),
  },
  blueprint: {
    body: (
      <>
        <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z" />
      </>
    ),
  },
  package: {
    body: (
      <>
        <path d="m7.5 4.27 9 5.15" />
        <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
        <path d="m3.3 7 8.7 5 8.7-5" />
        <path d="M12 22V12" />
      </>
    ),
  },
  manifest: {
    body: (
      <>
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <path d="M14 2v6h6" />
        <path d="M8 13h8" />
        <path d="M8 17h8" />
        <path d="M8 9h2" />
      </>
    ),
  },
  back: {
    body: (
      <>
        <path d="m12 19-7-7 7-7" />
        <path d="M19 12H5" />
      </>
    ),
  },
  attachment: {
    body: (
      <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    ),
  },
  reference: {
    body: (
      <>
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </>
    ),
  },
  record: {
    body: (
      <>
        <circle cx="12" cy="12" r="9" />
        <circle cx="12" cy="12" r="3" fill="currentColor" />
      </>
    ),
  },
};

export function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  const node = ICONS[name];
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={node.fill ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth={node.fill ? 0 : 2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {node.body}
    </svg>
  );
}
