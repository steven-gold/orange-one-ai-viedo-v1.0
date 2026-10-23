"use client";

import { useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { isAiUnavailable } from "@/lib/aiReply";
import { foldedMessagePreview, shouldFoldMessage } from "@/lib/conversationMarkdown";
import { ConversationFileActions } from "./ConversationFileActions";
import { ConversationMarkdown } from "./ConversationMarkdown";
import styles from "./conversationFileUi.module.css";

export function ConversationMessageBody({
  text,
  role,
  accountUid,
  sessionUid,
  tx,
  onRetry,
  onRegenerate,
  busy = false,
}: {
  text: string;
  role: "user" | "assistant";
  accountUid: string;
  sessionUid: string;
  tx: (key: TranslationKey) => string;
  onRetry?: () => void;
  onRegenerate?: () => void;
  busy?: boolean;
}) {
  const unavailable = role === "assistant" && isAiUnavailable(text);
  const display = unavailable ? tx("ai.unavailable") : text;
  const foldable = shouldFoldMessage(display);
  const [expanded, setExpanded] = useState(false);
  const shown = foldable && !expanded ? foldedMessagePreview(display) : display;
  const failed = role === "assistant" && (/狀態：失敗/u.test(text) || /失敗原因：/u.test(text));
  return (
    <>
      <ConversationMarkdown text={shown} />
      {foldable ? (
        <button type="button" className={styles.fileLink} onClick={() => setExpanded((value) => !value)}>
          {expanded ? tx("conversation.message.collapse") : tx("conversation.message.expand")}
        </button>
      ) : null}
      {role === "assistant" ? (
        <>
          <ConversationFileActions text={text} accountUid={accountUid} sessionUid={sessionUid} tx={tx} />
          {failed && onRetry ? (
            <div className={styles.fileActions}>
              <button type="button" className={styles.fileLink} disabled={busy} onClick={onRetry}>
                {tx("conversation.message.retry")}
              </button>
            </div>
          ) : null}
          {onRegenerate ? (
            <div className={styles.fileActions}>
              <button type="button" className={styles.fileLink} disabled={busy} onClick={onRegenerate}>
                {tx("conversation.message.regenerate")}
              </button>
            </div>
          ) : null}
        </>
      ) : null}
    </>
  );
}
