"use client";

export default function ErrorBoundary({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 32, background: "#070b14", color: "#f7f9fc" }}>
      <section role="alert" aria-live="assertive" style={{ width: "min(640px, 100%)", border: "1px solid rgba(255,255,255,.14)", borderRadius: 14, padding: 24, background: "rgba(255,255,255,.04)" }}>
        <div style={{ fontSize: 12, letterSpacing: ".12em", opacity: .7 }}>ORANGE ONE · ACPOS</div>
        <h1 style={{ margin: "12px 0 8px", fontSize: 24 }}>系統暫時無法完成此操作</h1>
        <p style={{ margin: "0 0 20px", lineHeight: 1.6, opacity: .82 }}>請重新嘗試。若問題持續發生，請保留目前操作時間與相關 Correlation ID 供管理者查核。</p>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button type="button" onClick={reset} style={{ border: 0, borderRadius: 8, padding: "10px 16px", cursor: "pointer", fontWeight: 700 }}>重新嘗試</button>
          <a href="/" style={{ border: "1px solid rgba(255,255,255,.22)", borderRadius: 8, padding: "9px 16px", color: "inherit", textDecoration: "none" }}>返回首頁</a>
        </div>
      </section>
    </main>
  );
}
