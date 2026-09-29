"use client";

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="zh-Hant-TW">
      <body style={{ margin: 0, background: "#070b14", color: "#f7f9fc", fontFamily: "system-ui, sans-serif" }}>
        <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 32 }}>
          <section role="alert" aria-live="assertive" style={{ width: "min(640px, 100%)", border: "1px solid rgba(255,255,255,.14)", borderRadius: 14, padding: 24, background: "rgba(255,255,255,.04)" }}>
            <div style={{ fontSize: 12, letterSpacing: ".12em", opacity: .7 }}>ORANGE ONE · ACPOS</div>
            <h1 style={{ margin: "12px 0 8px", fontSize: 24 }}>系統介面發生錯誤</h1>
            <p style={{ margin: "0 0 20px", lineHeight: 1.6, opacity: .82 }}>目前不顯示內部錯誤細節。請重新嘗試，若持續發生請交由系統管理者依稽核紀錄追查。</p>
            <button type="button" onClick={reset} style={{ border: 0, borderRadius: 8, padding: "10px 16px", cursor: "pointer", fontWeight: 700 }}>重新載入</button>
          </section>
        </main>
      </body>
    </html>
  );
}
