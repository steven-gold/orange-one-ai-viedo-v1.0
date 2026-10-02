import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ACPOS Global Home",
  description: "GLOBAL-HOME-SHELL-NAVIGATION runtime",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-TW">
      <body>{children}</body>
    </html>
  );
}
