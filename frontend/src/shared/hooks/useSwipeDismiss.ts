import { useRef, useState, useCallback } from "react";

type Phase = "idle" | "maybe" | "dragging";

interface UseSwipeDismissOptions {
	onClose: () => void;
	/** Distance threshold to trigger close (px). Default: 120 */
	threshold?: number;
	/** Drag resistance factor (0-1). Lower = more resistance. Default: 0.6 */
	resistance?: number;
	/** Velocity threshold to trigger close (px/ms). Default: 0.5 */
	velocityThreshold?: number;
	/** Ref to the scrollable content area. Swipe only activates when scrollTop === 0 */
	scrollRef?: React.RefObject<HTMLElement | null>;
	/** Enable/disable the gesture. Default: true */
	enabled?: boolean;
}

interface UseSwipeDismissReturn {
	/** Current Y offset in px. Apply as translateY on the sheet body. */
	dragOffset: number;
	/** Whether a drag gesture is active. Use to toggle CSS transitions. */
	isDragging: boolean;
	/** Whether the close animation is playing. */
	isClosing: boolean;
	/** Spread these on the outermost touch-capturing element. */
	handlers: {
		onTouchStart: (e: React.TouchEvent) => void;
		onTouchMove: (e: React.TouchEvent) => void;
		onTouchEnd: (e: React.TouchEvent) => void;
	};
}

const DEAD_ZONE = 8; // px before deciding direction
const TAP_TIME = 150; // ms
const TAP_DISTANCE = 5; // px

export function useSwipeDismiss({
	onClose,
	threshold = 120,
	resistance = 0.6,
	velocityThreshold = 0.5,
	scrollRef,
	enabled = true,
}: UseSwipeDismissOptions): UseSwipeDismissReturn {
	const [dragOffset, setDragOffset] = useState(0);
	const [isDragging, setIsDragging] = useState(false);
	const [isClosing, setIsClosing] = useState(false);

	const phase = useRef<Phase>("idle");
	const startY = useRef(0);
	const startX = useRef(0);
	const startTime = useRef(0);
	const locked = useRef(false); // true = horizontal lock, gesture cancelled

	const onTouchStart = useCallback(
		(e: React.TouchEvent) => {
			if (!enabled || isClosing) return;
			if (e.touches.length > 1) return; // multi-touch → ignore

			// If an input is focused (keyboard open), don't intercept
			const active = document.activeElement;
			if (
				active instanceof HTMLInputElement ||
				active instanceof HTMLTextAreaElement
			) {
				return;
			}

			// Check scroll position: only activate when content is at the top
			if (scrollRef?.current) {
				const scrollEl =
					scrollRef.current.querySelector("[data-scrollbar]") ||
					scrollRef.current;
				if (scrollEl.scrollTop > 0) return;
			}

			phase.current = "maybe";
			startY.current = e.touches[0].clientY;
			startX.current = e.touches[0].clientX;
			startTime.current = Date.now();
			locked.current = false;
		},
		[enabled, isClosing, scrollRef],
	);

	const onTouchMove = useCallback(
		(e: React.TouchEvent) => {
			if (phase.current === "idle" || locked.current || isClosing) return;
			if (e.touches.length > 1) {
				// Multi-touch appeared mid-gesture → cancel
				phase.current = "idle";
				setDragOffset(0);
				setIsDragging(false);
				return;
			}

			const currentY = e.touches[0].clientY;
			const currentX = e.touches[0].clientX;
			const deltaY = currentY - startY.current;
			const deltaX = currentX - startX.current;

			if (phase.current === "maybe") {
				const totalDelta = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
				if (totalDelta < DEAD_ZONE) return; // Still in dead zone

				// Decide direction
				if (Math.abs(deltaX) > Math.abs(deltaY)) {
					// Horizontal → lock out this gesture
					locked.current = true;
					return;
				}
				if (deltaY < 0) {
					// Upward swipe → not a dismiss gesture
					locked.current = true;
					return;
				}

				// Confirmed downward vertical drag
				phase.current = "dragging";
				setIsDragging(true);
			}

			if (phase.current === "dragging") {
				const rawDelta = Math.max(0, currentY - startY.current);
				setDragOffset(rawDelta * resistance);
			}
		},
		[resistance, isClosing],
	);

	const onTouchEnd = useCallback(
		(e: React.TouchEvent) => {
			if (phase.current === "idle" || locked.current) {
				phase.current = "idle";
				return;
			}

			const endY = e.changedTouches[0].clientY;
			const deltaY = endY - startY.current;
			const elapsed = Date.now() - startTime.current;

			// Quick tap → ignore
			if (elapsed < TAP_TIME && Math.abs(deltaY) < TAP_DISTANCE) {
				phase.current = "idle";
				setDragOffset(0);
				setIsDragging(false);
				return;
			}

			const velocity = deltaY / elapsed; // px/ms
			const effectiveThreshold = Math.min(threshold, window.innerHeight * 0.15);
			const shouldClose =
				dragOffset > effectiveThreshold || velocity > velocityThreshold;

			if (shouldClose) {
				// Close: animate off-screen
				setIsClosing(true);
				setDragOffset(window.innerHeight);
				setTimeout(() => {
					onClose();
					// Reset after close
					setDragOffset(0);
					setIsDragging(false);
					setIsClosing(false);
					phase.current = "idle";
				}, 200); // matches close animation duration
			} else {
				// Snap back
				setDragOffset(0);
				setIsDragging(false);
				phase.current = "idle";
			}
		},
		[dragOffset, threshold, velocityThreshold, onClose],
	);

	return {
		dragOffset,
		isDragging,
		isClosing,
		handlers: { onTouchStart, onTouchMove, onTouchEnd },
	};
}
