import {
	createContext,
	useContext,
	useEffect,
	useState,
	type ReactNode,
} from "react";

/**
 * One-shot mount animation for conditionally-rendered form content: the
 * block unfolds (CSS grid 0fr → 1fr) while fading in. Removal stays
 * instant on purpose — exit animations would mean keeping stale fields
 * mounted, which the huge listing form can't afford on low-end phones.
 * Styling lives in index.css (.ucm-reveal), including the
 * prefers-reduced-motion opt-out.
 */

const RevealGateContext = createContext(true);

/**
 * Suppresses the reveal for content that mounts together with the page
 * itself: children mounted during the first ~150ms render statically, so
 * the initial render (and edit-mode pre-fill) doesn't play an animation
 * storm. Anything mounted later — i.e. in response to user input — animates.
 */
export function RevealGate({ children }: { children: ReactNode }) {
	const [ready, setReady] = useState(false);
	useEffect(() => {
		const t = window.setTimeout(() => setReady(true), 150);
		return () => window.clearTimeout(t);
	}, []);
	return (
		<RevealGateContext.Provider value={ready}>
			{children}
		</RevealGateContext.Provider>
	);
}

export function Reveal({ children }: { children: ReactNode }) {
	// Captured once at mount — a block never re-animates when the gate flips.
	const [animate] = useState(useContext(RevealGateContext));
	// Clip overflow only while unfolding; once settled the wrapper must not
	// clip card shadows or inline dropdowns.
	const [settled, setSettled] = useState(false);
	if (!animate) return <>{children}</>;
	return (
		<div
			className="ucm-reveal"
			data-settled={settled || undefined}
			onAnimationEnd={(e) => {
				if (e.target === e.currentTarget) setSettled(true);
			}}
		>
			<div className="ucm-reveal-inner">{children}</div>
		</div>
	);
}
