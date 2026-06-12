import { useEffect, useRef } from "react";
import {
	backHandlerPushed,
	backHandlerRemoved,
} from "@shared/lib/telegram/backStack";

/**
 * Registers an open overlay (drawer / modal) in the Telegram Back-button
 * stack: while `opened` is true, the native Back button (and the Android
 * back gesture) closes this overlay instead of navigating. Overlays
 * stack — Back closes the topmost one first.
 *
 * Safe to call outside Telegram — the stack simply goes unused there.
 */
export function useTelegramBackClose(opened: boolean, onClose: () => void) {
	// Latest-callback ref: overlays recreate onClose every render; we must
	// not re-register (and reorder) the stack entry because of that.
	const onCloseRef = useRef(onClose);
	onCloseRef.current = onClose;

	useEffect(() => {
		if (!opened) return;
		const handler = () => onCloseRef.current();
		backHandlerPushed(handler);
		return () => {
			backHandlerRemoved(handler);
		};
	}, [opened]);
}
