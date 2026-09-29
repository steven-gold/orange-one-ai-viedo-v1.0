import type { Metadata } from "next";
import { LocaleProvider } from "@/i18n/LocaleProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "ORANGE ONE",
  description: "ACPOS",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-Hant-TW">
      <body><LocaleProvider>{children}</LocaleProvider></body>
    </html>
  );
}
