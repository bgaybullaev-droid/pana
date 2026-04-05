import { useRef, useCallback, useEffect } from "react";
import { Box, Text, type BoxProps } from "@mantine/core";

const COUNTRY_CODE = "+998";
const PREFIX = "+998 ";
const PREFIX_LEN = PREFIX.length;

function formatDigits(digits: string): string {
	const d = digits.slice(0, 9);
	const parts: string[] = [];
	if (d.length > 0) parts.push(d.slice(0, 2));
	if (d.length > 2) parts.push(d.slice(2, 5));
	if (d.length > 5) parts.push(d.slice(5, 7));
	if (d.length > 7) parts.push(d.slice(7, 9));
	return parts.join(" ");
}

function toDisplay(raw: string): string {
	const digits = raw.replace(/\D/g, "").replace(/^998/, "").slice(0, 9);
	const formatted = formatDigits(digits);
	return formatted ? `${PREFIX}${formatted}` : PREFIX;
}

function toRaw(input: string): string {
	const allDigits = input.replace(/\D/g, "");
	const local = allDigits.replace(/^998/, "").slice(0, 9);
	return COUNTRY_CODE + local;
}

interface PhoneInputProps {
	value: string;
	onChange: (value: string) => void;
	label?: string;
	placeholder?: string;
	description?: string;
	error?: string | null | false;
	disabled?: boolean;
	w?: BoxProps["w"];
	onKeyDown?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
}

/**
 * Phone input with fixed +998 prefix.
 * Uses an uncontrolled native input to properly handle browser autofill/contact picker.
 */
export function PhoneInput({
	value,
	onChange,
	label,
	placeholder,
	description,
	error,
	disabled,
	w,
	onKeyDown: externalKeyDown,
}: PhoneInputProps) {
	const inputRef = useRef<HTMLInputElement>(null);
	const onChangeRef = useRef(onChange);
	onChangeRef.current = onChange;

	// Sync display value into native input when value prop changes externally
	useEffect(() => {
		const el = inputRef.current;
		if (!el || document.activeElement === el) return;
		el.value = toDisplay(value);
	}, [value]);

	// Set initial value
	useEffect(() => {
		const el = inputRef.current;
		if (!el) return;
		el.value = toDisplay(value);
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	const syncFromInput = useCallback(() => {
		const el = inputRef.current;
		if (!el) return;
		const raw = toRaw(el.value);
		onChangeRef.current(raw);
		// Reformat the display
		const formatted = toDisplay(raw);
		if (el.value !== formatted) {
			const prevPos = el.selectionStart ?? formatted.length;
			el.value = formatted;
			// Adjust cursor
			let pos = Math.max(prevPos, PREFIX_LEN);
			while (pos < formatted.length && formatted[pos] === " ") pos++;
			pos = Math.min(pos, formatted.length);
			el.setSelectionRange(pos, pos);
		}
	}, []);

	const handleInput = useCallback(() => {
		syncFromInput();
	}, [syncFromInput]);

	const handleFocus = useCallback(() => {
		requestAnimationFrame(() => {
			const el = inputRef.current;
			if (!el) return;
			if (!el.value || el.value.length < PREFIX_LEN) {
				el.value = PREFIX;
			}
			if ((el.selectionStart ?? 0) < PREFIX_LEN) {
				el.setSelectionRange(PREFIX_LEN, PREFIX_LEN);
			}
		});
	}, []);

	const handleClick = useCallback(() => {
		const el = inputRef.current;
		if (!el) return;
		if ((el.selectionStart ?? 0) < PREFIX_LEN) {
			el.setSelectionRange(PREFIX_LEN, PREFIX_LEN);
		}
	}, []);

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent<HTMLInputElement>) => {
			const el = e.currentTarget;
			const pos = el.selectionStart ?? 0;
			const selEnd = el.selectionEnd ?? 0;

			if (e.key === "Backspace" && pos <= PREFIX_LEN && pos === selEnd) {
				e.preventDefault();
				return;
			}
			if (e.key === "ArrowLeft" && pos <= PREFIX_LEN) {
				e.preventDefault();
				return;
			}
			if (e.key === "Home") {
				e.preventDefault();
				el.setSelectionRange(PREFIX_LEN, PREFIX_LEN);
			}
			externalKeyDown?.(e);
		},
		[externalKeyDown],
	);

	const handlePaste = useCallback(
		(e: React.ClipboardEvent<HTMLInputElement>) => {
			e.preventDefault();
			const pasted = e.clipboardData.getData("text");
			const raw = toRaw(pasted);
			onChangeRef.current(raw);
			const el = inputRef.current;
			if (el) {
				el.value = toDisplay(raw);
				const end = el.value.length;
				el.setSelectionRange(end, end);
			}
		},
		[],
	);

	// Catch delayed autofill (contact picker) via blur
	const handleBlur = useCallback(() => {
		syncFromInput();
	}, [syncFromInput]);

	// Catch autofill/contact picker via multiple strategies
	useEffect(() => {
		const el = inputRef.current;
		if (!el) return;

		// 'change' event fires after browser autofill completes
		const handleChange = () => syncFromInput();
		el.addEventListener("change", handleChange);

		// animationstart fires when autofill applies :-webkit-autofill
		const handleAnimation = (e: AnimationEvent) => {
			if (e.animationName?.includes("auto-fill") || e.animationName?.includes("autofill")) {
				syncFromInput();
			}
		};
		el.addEventListener("animationstart", handleAnimation as EventListener);

		// Fast polling as fallback (every 50ms for first 3 seconds)
		let prevVal = el.value;
		const interval = setInterval(() => {
			if (el.value !== prevVal) {
				prevVal = el.value;
				syncFromInput();
			}
		}, 50);
		const timeout = setTimeout(() => clearInterval(interval), 3000);

		return () => {
			el.removeEventListener("change", handleChange);
			el.removeEventListener("animationstart", handleAnimation as EventListener);
			clearInterval(interval);
			clearTimeout(timeout);
		};
	}, [syncFromInput]);

	return (
		<Box w={w}>
			{label && (
				<Text size="sm" fw={500} mb={4}>
					{label}
				</Text>
			)}
			{description && (
				<Text size="xs" c="dimmed" mb={4}>
					{description}
				</Text>
			)}
			<input
				ref={inputRef}
				type="text"
				inputMode="numeric"
				autoComplete="off"
				data-form-type="other"
				data-lpignore="true"
				placeholder={placeholder || "+998 XX XXX XX XX"}
				disabled={disabled}
				onInput={handleInput}
				onFocus={handleFocus}
				onClick={handleClick}
				onKeyDown={handleKeyDown}
				onPaste={handlePaste}
				onBlur={handleBlur}
				className="phone-input"
				style={{
					width: "100%",
					height: 42,
					padding: "0 16px",
					fontSize: 16,
					fontFamily: "inherit",
					borderRadius: 9999,
					border: error
						? "1.5px solid var(--mantine-color-red-6)"
						: "1.5px solid var(--mantine-color-gray-2)",
					outline: "none",
					backgroundColor: disabled ? "#f8f9fa" : "white",
					color: disabled ? "#868e96" : "inherit",
					transition: "border-color 0.2s ease, box-shadow 0.2s ease",
				}}
				onFocusCapture={(e) => {
					const el = e.currentTarget;
					el.style.borderColor = "var(--mantine-color-blue-5)";
					el.style.boxShadow = "0 0 0 3px rgba(64, 167, 227, 0.1)";
				}}
				onBlurCapture={(e) => {
					const el = e.currentTarget;
					el.style.borderColor = error
						? "var(--mantine-color-red-6)"
						: "var(--mantine-color-gray-2)";
					el.style.boxShadow = "none";
				}}
			/>
			{error && typeof error === "string" && (
				<Text size="xs" c="red" mt={4}>
					{error}
				</Text>
			)}
		</Box>
	);
}
