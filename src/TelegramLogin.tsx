import { useEffect, useRef } from "react";

declare global {
  interface Window {
    onTelegramAuth?: (user: any) => void;
  }
}

export function TelegramLogin({
  botUsername,
  onLoggedIn,
}: {
  botUsername: string;
  onLoggedIn: () => void;
}) {
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
        else alert(data.error || "登入失敗");
      } catch (e) {
        alert("登入發生錯誤，請稍後再試");
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
