"use client";

import { useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { downloadConversationFile, fetchConversationFile } from "@/lib/client";
import { parseConversationFileRef } from "@/lib/conversationTask";
import styles from "./conversationFileUi.module.css";

export function ConversationFileActions({
  text,
  accountUid,
  sessionUid,
  tx,
}: {
  text: string;
  accountUid: string;
  sessionUid: string;
  tx: (key: TranslationKey) => string;
}) {
  const ref = parseConversationFileRef(text);
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  if (!ref) return null;

  const readFile = async () => {
    setBusy(true);
    setError(false);
    try {
      const file = await fetchConversationFile(accountUid, ref.fileId, sessionUid);
      setBody(file.body);
      setOpen(true);
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  };

  const downloadFile = async () => {
    setBusy(true);
    setError(false);
    try {
      await downloadConversationFile(accountUid, ref.fileId, ref.fileName, sessionUid);
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className={styles.fileActions}>
        <button type="button" className={styles.fileLink} disabled={busy} onClick={() => void readFile()}>
          {tx("conversation.file.read")}
        </button>
        <button type="button" className={styles.fileLink} disabled={busy} onClick={() => void downloadFile()}>
          {tx("conversation.file.download")}
        </button>
      </div>
      {error ? <p className={styles.error}>{tx("conversation.file.unavailable")}</p> : null}
      {open ? (
        <div className={styles.dialogScrim} role="presentation" onClick={() => setOpen(false)}>
          <section className={styles.dialog} onClick={(event) => event.stopPropagation()}>
            <h2>{ref.fileName || tx("conversation.file.title")}</h2>
            <pre className={styles.fileBody}>{body}</pre>
            <div className={styles.dialogActions}>
              <button type="button" className={styles.btn} onClick={() => void downloadFile()}>
                {tx("conversation.file.download")}
              </button>
              <button type="button" className={styles.btn} onClick={() => setOpen(false)}>
                {tx("conversation.file.close")}
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </>
  );
}
