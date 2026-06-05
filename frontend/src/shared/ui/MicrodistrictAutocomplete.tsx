/**
 * Microdistrict autocomplete for the seller listing form.
 *
 * Mirrors {@link ./HousingComplexAutocomplete} (TextInput + custom dropdown),
 * but the suggestion source is the local {@link @shared/constants/microdistricts}
 * registry rather than a network lookup — no debounce / fetch needed.
 *
 * UX contract:
 *   - Suggestions are scoped to the район→микрорайон cascade: when a Tashkent
 *     `district` is selected, only that district's entries are offered; if no
 *     district is set the field stays free-text with no hints.
 *   - Typing filters the scoped list by case-insensitive substring.
 *   - Picking a suggestion → `onChange(<name>)`.
 *   - Free-text is allowed: any value the user types is emitted as-is, so a
 *     name missing from the registry is still accepted.
 *   - Empty input → `onChange(undefined)`.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { Box, Paper, Text, TextInput } from "@mantine/core";
import { MICRODISTRICTS } from "@shared/constants/microdistricts";

export interface MicrodistrictAutocompleteProps {
	value: string | undefined;
	onChange: (next: string | undefined) => void;
	label?: string;
	placeholder?: string;
	/** Tashkent-city district key used to scope the suggestion list. When
	 *  omitted, no suggestions are shown (free-text only). */
	district?: string | undefined;
	disabled?: boolean;
}

const MAX_RESULTS = 10;

export function MicrodistrictAutocomplete({
	value,
	onChange,
	label,
	placeholder,
	district,
	disabled,
}: MicrodistrictAutocompleteProps) {
	const [text, setText] = useState<string>(value ?? "");
	const [open, setOpen] = useState(false);
	const boxRef = useRef<HTMLDivElement>(null);

	// Re-sync when the parent updates the value externally (edit-mode pre-fill).
	useEffect(() => {
		setText(value ?? "");
	}, [value]);

	// Close dropdown on outside-click.
	useEffect(() => {
		function handleClick(e: MouseEvent) {
			if (!boxRef.current) return;
			if (!boxRef.current.contains(e.target as Node)) {
				setOpen(false);
			}
		}
		document.addEventListener("mousedown", handleClick);
		return () => document.removeEventListener("mousedown", handleClick);
	}, []);

	// Scope to the selected district, then filter by substring. Without a
	// district there is nothing meaningful to suggest, so the list stays empty
	// and the field behaves as plain free-text input.
	const results = useMemo(() => {
		if (!district) return [];
		const scoped = MICRODISTRICTS.filter((m) => m.district === district);
		const q = text.trim().toLowerCase();
		const matched = q
			? scoped.filter((m) => m.name.toLowerCase().includes(q))
			: scoped;
		return matched.slice(0, MAX_RESULTS);
	}, [district, text]);

	const handleChange = (raw: string) => {
		setText(raw);
		onChange(raw.trim() || undefined);
		setOpen(true);
	};

	const handlePick = (name: string) => {
		setText(name);
		setOpen(false);
		onChange(name);
	};

	return (
		<Box ref={boxRef} style={{ position: "relative" }}>
			<TextInput
				label={label}
				placeholder={placeholder}
				value={text}
				onChange={(e) => handleChange(e.currentTarget.value)}
				onFocus={() => {
					if (results.length > 0) setOpen(true);
				}}
				disabled={disabled}
			/>
			{open && results.length > 0 && (
				<Paper
					shadow="sm"
					withBorder
					style={{
						position: "absolute",
						top: "100%",
						left: 0,
						right: 0,
						marginTop: 4,
						zIndex: 1000,
						maxHeight: 280,
						overflowY: "auto",
					}}
				>
					{results.map((item) => (
						<Box
							key={`${item.district}:${item.name}`}
							onClick={() => handlePick(item.name)}
							style={{
								padding: "8px 12px",
								cursor: "pointer",
							}}
							onMouseEnter={(e) => {
								(e.currentTarget as HTMLElement).style.backgroundColor =
									"#f1f3f5";
							}}
							onMouseLeave={(e) => {
								(e.currentTarget as HTMLElement).style.backgroundColor = "";
							}}
						>
							<Text size="sm" fw={500}>
								{item.name}
							</Text>
						</Box>
					))}
				</Paper>
			)}
		</Box>
	);
}
