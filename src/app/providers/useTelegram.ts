import { useContext } from 'react';
import { TelegramContext } from './TelegramProvider';

export function useTelegram() {
  return useContext(TelegramContext);
}
