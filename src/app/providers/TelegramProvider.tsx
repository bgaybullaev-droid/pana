import { createContext, useEffect, useState, ReactNode } from 'react';
import { WebApp, WebAppUser } from '@shared/lib/telegram/types';

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
  initData: '',
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
    const tg = (window as any).Telegram?.WebApp as WebApp | undefined;

    if (tg) {
      // Initialize Telegram WebApp
      tg.ready();
      tg.expand();

      // Set theme colors
      if (tg.themeParams) {
        document.documentElement.style.setProperty(
          '--tg-theme-bg-color',
          tg.themeParams.bg_color || '#ffffff'
        );
        document.documentElement.style.setProperty(
          '--tg-theme-text-color',
          tg.themeParams.text_color || '#000000'
        );
        document.documentElement.style.setProperty(
          '--tg-theme-button-color',
          tg.themeParams.button_color || '#228be6'
        );
        document.documentElement.style.setProperty(
          '--tg-theme-button-text-color',
          tg.themeParams.button_text_color || '#ffffff'
        );
      }

      setWebApp(tg);
      setIsReady(true);
    } else {
      // Not in Telegram - development mode
      console.warn('Telegram WebApp not available. Running in development mode.');
      setIsReady(true);
    }
  }, []);

  const value: TelegramContextValue = {
    webApp,
    user: webApp?.initDataUnsafe?.user || null,
    initData: webApp?.initData || '',
    isReady,
    isTelegramWebApp: !!webApp,
  };

  return (
    <TelegramContext.Provider value={value}>
      {children}
    </TelegramContext.Provider>
  );
}
