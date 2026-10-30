"use client";

import { useEffect } from "react";

type TelegramWebApp = {
  ready: () => void;
  expand: () => void;
};

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

function showMiniApp() {
  const webApp = window.Telegram?.WebApp;
  if (!webApp) return false;
  webApp.ready();
  webApp.expand();
  return true;
}

export function TelegramBootstrap() {
  useEffect(() => {
    if (!document.querySelector("script[data-telegram-web-app]")) {
      const script = document.createElement("script");
      script.src = "https://telegram.org/js/telegram-web-app.js";
      script.async = true;
      script.dataset.telegramWebApp = "true";
      document.head.appendChild(script);
    }

    if (showMiniApp()) return;

    const timer = window.setInterval(() => {
      if (showMiniApp()) window.clearInterval(timer);
    }, 50);
    const stop = window.setTimeout(() => window.clearInterval(timer), 5000);

    return () => {
      window.clearInterval(timer);
      window.clearTimeout(stop);
    };
  }, []);

  return null;
}
