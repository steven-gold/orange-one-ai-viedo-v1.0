export default function NotFound() {
  return (
    <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 32, background: "#070b14", color: "#f7f9fc" }}>
      <section style={{ width: "min(640px, 100%)", border: "1px solid rgba(255,255,255,.14)", borderRadius: 14, padding: 24, background: "rgba(255,255,255,.04)" }}>
        <div style={{ fontSize: 12, letterSpacing: ".12em", opacity: .7 }}>ORANGE ONE · ACPOS</div>
        <h1 style={{ margin: "12px 0 8px", fontSize: 24 }}>找不到此頁面</h1>
        <p style={{ margin: "0 0 20px", lineHeight: 1.6, opacity: .82 }}>此路徑不屬於目前 ACPOS Current Navigation。請返回首頁或使用正式導覽進入功能。</p>
        <a href="/" style={{ display: "inline-block", border: "1px solid rgba(255,255,255,.22)", borderRadius: 8, padding: "9px 16px", color: "inherit", textDecoration: "none" }}>返回首頁</a>
      </section>
    </main>
  );
}
