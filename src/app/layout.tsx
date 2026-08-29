import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ORANGE ONE",
  description: "ACPOS",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-TW">
      <body>{children}</body>
    </html>
  );
}
