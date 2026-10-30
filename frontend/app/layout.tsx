import type { ReactNode } from "react";
import Script from "next/script";
import "xp.css/dist/XP.css";
import { TelegramBootstrap } from "./telegram";
import "./globals.css";

export const metadata = {
  title: "Каталог",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body>
        <Script src="https://telegram.org/js/telegram-web-app.js" strategy="beforeInteractive" />
        <TelegramBootstrap />
        {children}
      </body>
    </html>
  );
}
