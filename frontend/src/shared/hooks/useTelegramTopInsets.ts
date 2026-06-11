import { useEffect, useState } from "react";
import { useTelegram } from "@app/providers/useTelegram";

interface TopInsets {
	/** Device status bar / notch height in px. */
	top: number;
	/** Height of Telegram's own controls row (Back / Close / minimize) in
	 *  fullscreen mode; 0 in regular browsers and non-fullscreen Telegram,
	 *  so `contentTop > 0` doubles as a fullscreen-mode flag. */
	contentTop: number;
}

/**
 * Live top insets reported by the Telegram client (Bot API 8.0+).
 * Subscribes to safe-area / fullscreen events so values follow rotation
 * and fullscreen toggles. Returns zeros outside Telegram.
 */
export function useTelegramTopInsets(): TopInsets {
	const { webApp } = useTelegram();
	const [insets, setInsets] = useState<TopInsets>(() => ({
		top: webApp?.safeAreaInset?.top ?? 0,
		contentTop: webApp?.contentSafeAreaInset?.top ?? 0,
	}));

	useEffect(() => {
		if (!webApp) return;
		// Functional update with a bail-out: consumers (and tests) may hand us
		// a webApp whose identity changes every render — re-setting an equal
		// state object would loop the render cycle forever.
		const update = () =>
			setInsets((prev) => {
				const top = webApp.safeAreaInset?.top ?? 0;
				const contentTop = webApp.contentSafeAreaInset?.top ?? 0;
				return prev.top === top && prev.contentTop === contentTop
					? prev
					: { top, contentTop };
			});
		update();
		// Very old clients expose no event bus — static values still apply.
		if (
			typeof webApp.onEvent !== "function" ||
			typeof webApp.offEvent !== "function"
		)
			return;
		const events = [
			"safeAreaChanged",
			"contentSafeAreaChanged",
			"fullscreenChanged",
		];
		events.forEach((e) => webApp.onEvent(e, update));
		return () => events.forEach((e) => webApp.offEvent(e, update));
	}, [webApp]);

	return insets;
}
