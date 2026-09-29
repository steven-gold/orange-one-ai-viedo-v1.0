export default function Loading() {
  return (
    <main aria-live="polite" aria-busy="true" style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 32, background: "#070b14", color: "#f7f9fc" }}>
      <div style={{ opacity: .78 }}>ORANGE ONE · ACPOS 正在載入…</div>
    </main>
  );
}
