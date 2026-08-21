import { useEffect, useRef } from "react";
import { useI18n, Language } from "./i18n";

declare global {
  interface Window {
    onTelegramAuth?: (user: any) => void;
  }
}

export function TelegramLogin({
  botUsername,
  userLang,
  onLoggedIn,
}: {
  botUsername: string;
  userLang: Language;
  onLoggedIn: () => void;
}) {
  const { t } = useI18n(userLang);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!botUsername || !ref.current) return;
    const container = ref.current;
    container.innerHTML = "";
    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.async = true;
    script.setAttribute("data-telegram-login", botUsername);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    script.setAttribute("data-request-access", "write");

    window.onTelegramAuth = async (user: any) => {
      try {
        const res = await fetch("/api/auth/telegram-login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(user),
        });
        const data = await res.json();
        if (data.success) onLoggedIn();
        else alert(data.error || t('tg_login_failed'));
      } catch (e) {
        alert(t('tg_login_error'));
      }
    };

    container.appendChild(script);
    return () => {
      container.innerHTML = "";
      delete window.onTelegramAuth;
    };
  }, [botUsername, onLoggedIn]);

  return <div ref={ref} />;
}
