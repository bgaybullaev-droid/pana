import { createContext, useEffect, useState, ReactNode } from "react";
import { WebApp, WebAppUser } from "@shared/lib/telegram/types";

interface TelegramContextValue {
	webApp: WebApp | null;
	user: WebAppUser | null;
	initData: string;
	isReady: boolean;
	isTelegramWebApp: boolean;
}

export const TelegramContext = createContext<TelegramContextValue>({
	webApp: null,
	user: null,
	initData: "",
	isReady: false,
	isTelegramWebApp: false,
});

interface TelegramProviderProps {
	children: ReactNode;
}

export function TelegramProvider({ children }: TelegramProviderProps) {
	const [webApp, setWebApp] = useState<WebApp | null>(null);
	const [isReady, setIsReady] = useState(false);

	useEffect(() => {
		function initTelegram() {
			const tg = (window as any).Telegram?.WebApp as WebApp | undefined;

			if (tg) {
				tg.ready();
				tg.expand();

				if (tg.themeParams) {
					document.documentElement.style.setProperty(
						"--tg-theme-bg-color",
						tg.themeParams.bg_color || "#ffffff",
					);
					document.documentElement.style.setProperty(
						"--tg-theme-text-color",
						tg.themeParams.text_color || "#000000",
					);
					document.documentElement.style.setProperty(
						"--tg-theme-button-color",
						tg.themeParams.button_color || "#228be6",
					);
					document.documentElement.style.setProperty(
						"--tg-theme-button-text-color",
						tg.themeParams.button_text_color || "#ffffff",
					);
				}

				setWebApp(tg);
				setIsReady(true);
				return true;
			}
			return false;
		}

		// Try immediately (script may already be loaded)
		if (initTelegram()) return;

		// Script loads async — wait up to 1.5s for it, then proceed without it
		let attempts = 0;
		const interval = setInterval(() => {
			attempts++;
			if (initTelegram() || attempts >= 15) {
				clearInterval(interval);
				if (!isReady) {
					// Telegram SDK didn't load — running outside Telegram
					setIsReady(true);
				}
			}
		}, 100);

		return () => clearInterval(interval);
	}, []);

	// telegram-web-app.js injects a stub on ANY page (empty initData,
	// platform "unknown"), so `!!webApp` is true even in a regular
	// browser. Only treat this as a real Telegram WebApp when initData
	// is present or the platform is a known client.
	const initData = webApp?.initData || "";
	const platform = (webApp as any)?.platform || "unknown";
	const isTelegramWebApp =
		!!webApp && (initData.length > 0 || platform !== "unknown");

	const value: TelegramContextValue = {
		webApp,
		user: webApp?.initDataUnsafe?.user || null,
		initData,
		isReady,
		isTelegramWebApp,
	};

	return (
		<TelegramContext.Provider value={value}>
			{children}
		</TelegramContext.Provider>
	);
}
