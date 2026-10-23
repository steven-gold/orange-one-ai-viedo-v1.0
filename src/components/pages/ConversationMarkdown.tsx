"use client";

import type { ReactNode } from "react";
import {
  parseConversationMarkdown,
  parseInlineMarkdown,
  type ConversationInlinePart,
  type ConversationMarkdownNode,
} from "@/lib/conversationMarkdown";
import styles from "./conversationFileUi.module.css";

function Inline({ text }: { text: string }) {
  return (
    <>
      {parseInlineMarkdown(text).map((part: ConversationInlinePart, index) => {
        if (part.type === "strong") return <strong key={index}>{part.text}</strong>;
        if (part.type === "em") return <em key={index}>{part.text}</em>;
        if (part.type === "code") return <code key={index}>{part.text}</code>;
        return <span key={index}>{part.text}</span>;
      })}
    </>
  );
}

function nodeView(node: ConversationMarkdownNode, index: number): ReactNode {
  if (node.type === "h") {
    if (node.level === 1) return <h3 key={index}><Inline text={node.text} /></h3>;
    if (node.level === 2) return <h4 key={index}><Inline text={node.text} /></h4>;
    return <h5 key={index}><Inline text={node.text} /></h5>;
  }
  if (node.type === "ul") {
    return (
      <ul key={index}>
        {node.items.map((item, itemIndex) => (
          <li key={itemIndex}><Inline text={item} /></li>
        ))}
      </ul>
    );
  }
  if (node.type === "ol") {
    return (
      <ol key={index}>
        {node.items.map((item, itemIndex) => (
          <li key={itemIndex}><Inline text={item} /></li>
        ))}
      </ol>
    );
  }
  if (node.type === "pre") return <pre key={index}>{node.text}</pre>;
  if (node.type === "quote") {
    return (
      <blockquote key={index}>
        <Inline text={node.text} />
      </blockquote>
    );
  }
  if (node.type === "table") {
    return (
      <table key={index}>
        <thead>
          <tr>
            {node.headers.map((cell, cellIndex) => (
              <th key={cellIndex}><Inline text={cell} /></th>
            ))}
          </tr>
        </thead>
        <tbody>
          {node.rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex}><Inline text={cell} /></td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    );
  }
  return (
    <p key={index}>
      <Inline text={node.text} />
    </p>
  );
}

export function ConversationMarkdown({ text }: { text: string }) {
  return <div className={styles.markdown}>{parseConversationMarkdown(text).map(nodeView)}</div>;
}
