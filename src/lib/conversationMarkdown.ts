export const LONG_MESSAGE_FOLD_CHARS = 800;
export const LONG_MESSAGE_FOLD_LINES = 12;

export type ConversationMarkdownNode =
  | { type: "p"; text: string }
  | { type: "h"; level: 1 | 2 | 3; text: string }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[] }
  | { type: "pre"; text: string }
  | { type: "quote"; text: string }
  | { type: "table"; headers: string[]; rows: string[][] };

function cleanLine(value: string): string {
  return value.replace(/\s+$/u, "");
}

function heading(line: string): ConversationMarkdownNode | null {
  const match = /^(#{1,3})\s+(.+)$/u.exec(line);
  if (!match) return null;
  const level = match[1].length as 1 | 2 | 3;
  return { type: "h", level, text: match[2].trim() };
}

function splitRow(line: string): string[] {
  const trimmed = line.trim().replace(/^\|/u, "").replace(/\|$/u, "");
  return trimmed.split("|").map((cell) => cell.trim());
}

function isTableDivider(line: string): boolean {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/u.test(line);
}

export function parseConversationMarkdown(source: string): ConversationMarkdownNode[] {
  const text = source.replace(/\r\n/gu, "\n");
  const lines = text.split("\n");
  const nodes: ConversationMarkdownNode[] = [];
  let index = 0;
  while (index < lines.length) {
    const raw = lines[index];
    const line = cleanLine(raw);
    if (!line.trim()) {
      index += 1;
      continue;
    }
    if (line.startsWith("```")) {
      const fence: string[] = [];
      index += 1;
      while (index < lines.length && !lines[index].startsWith("```")) {
        fence.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) index += 1;
      nodes.push({ type: "pre", text: fence.join("\n") });
      continue;
    }
    const title = heading(line);
    if (title) {
      nodes.push(title);
      index += 1;
      continue;
    }
    if (/^\s*>\s?/u.test(line)) {
      const quotes: string[] = [];
      while (index < lines.length && /^\s*>\s?/u.test(lines[index])) {
        quotes.push(lines[index].replace(/^\s*>\s?/u, ""));
        index += 1;
      }
      nodes.push({ type: "quote", text: quotes.join("\n") });
      continue;
    }
    if (/^\s*[-*]\s+/u.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\s*[-*]\s+/u.test(lines[index])) {
        items.push(lines[index].replace(/^\s*[-*]\s+/u, "").trim());
        index += 1;
      }
      nodes.push({ type: "ul", items });
      continue;
    }
    if (/^\s*\d+[.)]\s+/u.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\s*\d+[.)]\s+/u.test(lines[index])) {
        items.push(lines[index].replace(/^\s*\d+[.)]\s+/u, "").trim());
        index += 1;
      }
      nodes.push({ type: "ol", items });
      continue;
    }
    if (line.includes("|") && index + 1 < lines.length && isTableDivider(lines[index + 1])) {
      const headers = splitRow(line);
      index += 2;
      const rows: string[][] = [];
      while (index < lines.length && lines[index].includes("|") && !isTableDivider(lines[index])) {
        rows.push(splitRow(lines[index]));
        index += 1;
      }
      nodes.push({ type: "table", headers, rows });
      continue;
    }
    const para: string[] = [line];
    index += 1;
    while (
      index < lines.length &&
      lines[index].trim() &&
      !lines[index].startsWith("```") &&
      !heading(lines[index]) &&
      !/^\s*[-*]\s+/u.test(lines[index]) &&
      !/^\s*\d+[.)]\s+/u.test(lines[index]) &&
      !/^\s*>\s?/u.test(lines[index])
    ) {
      para.push(cleanLine(lines[index]));
      index += 1;
    }
    nodes.push({ type: "p", text: para.join("\n") });
  }
  return nodes.length ? nodes : [{ type: "p", text: source }];
}

export function shouldFoldMessage(text: string): boolean {
  const body = text.trim();
  if (!body) return false;
  if (body.length > LONG_MESSAGE_FOLD_CHARS) return true;
  return body.split("\n").length > LONG_MESSAGE_FOLD_LINES;
}

export function foldedMessagePreview(text: string): string {
  const body = text.trim();
  const byLine = body.split("\n").slice(0, LONG_MESSAGE_FOLD_LINES).join("\n");
  if (byLine.length <= LONG_MESSAGE_FOLD_CHARS) return byLine;
  return body.slice(0, LONG_MESSAGE_FOLD_CHARS);
}

export type ConversationInlinePart =
  | { type: "text"; text: string }
  | { type: "strong"; text: string }
  | { type: "em"; text: string }
  | { type: "code"; text: string };

export function parseInlineMarkdown(text: string): ConversationInlinePart[] {
  const parts: ConversationInlinePart[] = [];
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/gu;
  let last = 0;
  let match: RegExpExecArray | null = pattern.exec(text);
  while (match) {
    if (match.index > last) parts.push({ type: "text", text: text.slice(last, match.index) });
    const token = match[0];
    if (token.startsWith("**")) parts.push({ type: "strong", text: token.slice(2, -2) });
    else if (token.startsWith("`")) parts.push({ type: "code", text: token.slice(1, -1) });
    else parts.push({ type: "em", text: token.slice(1, -1) });
    last = match.index + token.length;
    match = pattern.exec(text);
  }
  if (last < text.length) parts.push({ type: "text", text: text.slice(last) });
  return parts.length ? parts : [{ type: "text", text }];
}
