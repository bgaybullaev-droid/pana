import { createEvent, createStore } from "effector";

/**
 * Stack of close-handlers for currently open overlays (drawers / modals).
 * While non-empty, Telegram's native Back button closes the topmost
 * overlay instead of navigating between pages (see
 * TelegramBackButtonManager in app/router/Router.tsx).
 */
export type BackCloseHandler = () => void;

export const backHandlerPushed = createEvent<BackCloseHandler>();
export const backHandlerRemoved = createEvent<BackCloseHandler>();

export const $backHandlers = createStore<BackCloseHandler[]>([])
	.on(backHandlerPushed, (stack, handler) => [...stack, handler])
	.on(backHandlerRemoved, (stack, handler) =>
		stack.filter((h) => h !== handler),
	);
