/**
 * Telegram WebApp API types
 * @see https://core.telegram.org/bots/webapps
 */

export interface WebAppUser {
  id: number;
  is_bot?: boolean;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium?: boolean;
  photo_url?: string;
}

export interface WebAppInitData {
  query_id?: string;
  user?: WebAppUser;
  receiver?: WebAppUser;
  chat?: {
    id: number;
    type: string;
    title?: string;
    username?: string;
    photo_url?: string;
  };
  start_param?: string;
  auth_date: number;
  hash: string;
}

export interface ThemeParams {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
}

export interface MainButton {
  text: string;
  color: string;
  textColor: string;
  isVisible: boolean;
  isActive: boolean;
  isProgressVisible: boolean;
  setText: (text: string) => MainButton;
  onClick: (callback: () => void) => MainButton;
  offClick: (callback: () => void) => MainButton;
  show: () => MainButton;
  hide: () => MainButton;
  enable: () => MainButton;
  disable: () => MainButton;
  showProgress: (leaveActive?: boolean) => MainButton;
  hideProgress: () => MainButton;
  setParams: (params: {
    text?: string;
    color?: string;
    text_color?: string;
    is_active?: boolean;
    is_visible?: boolean;
  }) => MainButton;
}

export interface BackButton {
  isVisible: boolean;
  onClick: (callback: () => void) => BackButton;
  offClick: (callback: () => void) => BackButton;
  show: () => BackButton;
  hide: () => BackButton;
}

export interface HapticFeedback {
  impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => HapticFeedback;
  notificationOccurred: (type: 'error' | 'success' | 'warning') => HapticFeedback;
  selectionChanged: () => HapticFeedback;
}

export interface CloudStorage {
  setItem: (key: string, value: string, callback?: (error: Error | null, success?: boolean) => void) => CloudStorage;
  getItem: (key: string, callback: (error: Error | null, value?: string) => void) => CloudStorage;
  getItems: (keys: string[], callback: (error: Error | null, values?: Record<string, string>) => void) => CloudStorage;
  removeItem: (key: string, callback?: (error: Error | null, success?: boolean) => void) => CloudStorage;
  removeItems: (keys: string[], callback?: (error: Error | null, success?: boolean) => void) => CloudStorage;
  getKeys: (callback: (error: Error | null, keys?: string[]) => void) => CloudStorage;
}

export interface WebApp {
  initData: string;
  initDataUnsafe: WebAppInitData;
  version: string;
  platform: string;
  colorScheme: 'light' | 'dark';
  themeParams: ThemeParams;
  isExpanded: boolean;
  viewportHeight: number;
  viewportStableHeight: number;
  headerColor: string;
  backgroundColor: string;
  isClosingConfirmationEnabled: boolean;
  BackButton: BackButton;
  MainButton: MainButton;
  HapticFeedback: HapticFeedback;
  CloudStorage: CloudStorage;

  isVersionAtLeast: (version: string) => boolean;
  setHeaderColor: (color: string) => void;
  setBackgroundColor: (color: string) => void;
  enableClosingConfirmation: () => void;
  disableClosingConfirmation: () => void;
  onEvent: (eventType: string, eventHandler: () => void) => void;
  offEvent: (eventType: string, eventHandler: () => void) => void;
  sendData: (data: string) => void;
  switchInlineQuery: (query: string, choose_chat_types?: string[]) => void;
  openLink: (url: string, options?: { try_instant_view?: boolean }) => void;
  openTelegramLink: (url: string) => void;
  openInvoice: (url: string, callback?: (status: string) => void) => void;
  showPopup: (params: {
    title?: string;
    message: string;
    buttons?: Array<{
      id?: string;
      type?: 'default' | 'ok' | 'close' | 'cancel' | 'destructive';
      text?: string;
    }>;
  }, callback?: (button_id: string) => void) => void;
  showAlert: (message: string, callback?: () => void) => void;
  showConfirm: (message: string, callback?: (confirmed: boolean) => void) => void;
  showScanQrPopup: (params: { text?: string }, callback?: (text: string) => boolean) => void;
  closeScanQrPopup: () => void;
  readTextFromClipboard: (callback?: (text: string) => void) => void;
  requestWriteAccess: (callback?: (granted: boolean) => void) => void;
  // Telegram clients vary: older ones invoke the callback with a boolean
  // (shared yes/no); newer ones invoke it with { status: "sent" | "cancelled" }.
  // The consumer normalizes both shapes.
  requestContact: (
    callback?: (
      result: boolean | { status: "sent" | "cancelled" | string },
    ) => void,
  ) => void;
  ready: () => void;
  expand: () => void;
  close: () => void;
}

declare global {
  interface Window {
    Telegram?: {
      WebApp: WebApp;
    };
  }
}
