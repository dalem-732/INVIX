import type { ReactNode } from "react";
import "xp.css";
import { TelegramBootstrap } from "./telegram";
import "./globals.css";

export const metadata = {
  title: "Каталог",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body>
        <TelegramBootstrap />
        {children}
      </body>
    </html>
  );
}
