/**
 * PR-F — Housing-complex autocomplete for the seller listing form.
 *
 * UX contract:
 *   - User types → 300ms debounce → /housing-complexes?q=... fetch.
 *   - Picking a suggestion → calls `onChange({ jk_id, jk_name })`.
 *   - Keeping a free-text value that doesn't match a suggestion → calls
 *     `onChange({ jk_id: undefined, jk_name: <text> })`. Backend accepts
 *     this during the dual-column window.
 *   - Empty input → `onChange({ jk_id: undefined, jk_name: undefined })`.
 *   - Network / server failure → dropdown silently disappears; user
 *     keeps typing in free-text mode (graceful degrade).
 *
 * We intentionally do NOT use Mantine's uncontrolled `Autocomplete`
 * because its `data` prop only supports string labels; we need to map
 * label → id on select. Built from `TextInput` + a custom dropdown.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { ActionIcon, Box, Loader, Paper, Text, TextInput } from "@mantine/core";
import { IconX } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import {
	searchHousingComplexes,
	type HousingComplexListItem,
} from "@shared/api/housingComplexes";

export interface HousingComplexSelection {
	jk_id: string | undefined;
	jk_name: string | undefined;
}

export interface HousingComplexAutocompleteProps {
	value: HousingComplexSelection;
	onChange: (next: HousingComplexSelection) => void;
	label?: string;
	placeholder?: string;
	/** Narrow the suggestion list to a specific region slug. Optional;
	 *  omit for a global catalog lookup. */
	region?: string | undefined;
	/** Narrow further by district slug (район→ЖК cascade). */
	district?: string | undefined;
	disabled?: boolean;
}

const DEBOUNCE_MS = 300;
const MIN_CHARS = 1;
const MAX_RESULTS = 10;

export function HousingComplexAutocomplete({
	value,
	onChange,
	label,
	placeholder,
	region,
	district,
	disabled,
}: HousingComplexAutocompleteProps) {
	const { t } = useTranslation("common");
	// The text input is controlled by jk_name — it always reflects what
	// the user sees, whether they typed it or picked from the dropdown.
	const [text, setText] = useState<string>(value.jk_name ?? "");
	const [results, setResults] = useState<HousingComplexListItem[]>([]);
	const [open, setOpen] = useState(false);
	const [loading, setLoading] = useState(false);
	const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const boxRef = useRef<HTMLDivElement>(null);

	// Re-sync text if the parent updates `value.jk_name` externally (e.g.
	// edit-mode pre-fill on a listing that already has jk_name stored).
	useEffect(() => {
		setText(value.jk_name ?? "");
	}, [value.jk_name]);

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

	const scheduleSearch = (q: string) => {
		if (debounceRef.current) clearTimeout(debounceRef.current);
		if (q.trim().length < MIN_CHARS) {
			setResults([]);
			setOpen(false);
			setLoading(false);
			return;
		}
		setLoading(true);
		debounceRef.current = setTimeout(async () => {
			const list = await searchHousingComplexes({
				q,
				region,
				district,
				limit: MAX_RESULTS,
			});
			setResults(list);
			setOpen(list.length > 0);
			setLoading(false);
		}, DEBOUNCE_MS);
	};

	const handleChange = (raw: string) => {
		setText(raw);
		// Typing invalidates any previously-selected jk_id — the user is
		// editing. We emit jk_name change immediately so the parent form
		// state stays in sync; jk_id goes undefined until they pick a
		// suggestion.
		onChange({
			jk_id: undefined,
			jk_name: raw.trim() || undefined,
		});
		scheduleSearch(raw);
	};

	const handlePick = (item: HousingComplexListItem) => {
		setText(item.name);
		setOpen(false);
		onChange({ jk_id: item.id, jk_name: item.name });
	};

	const description = useMemo(() => {
		if (!value.jk_id) return undefined;
		// Show a small cue that the user has a linked HC, not just free text.
		return t("housingComplex.linked");
	}, [value.jk_id, t]);

	return (
		<Box ref={boxRef} style={{ position: "relative" }}>
			<TextInput
				label={label}
				placeholder={placeholder}
				description={description}
				value={text}
				onChange={(e) => handleChange(e.currentTarget.value)}
				onFocus={() => {
					if (results.length > 0) setOpen(true);
				}}
				disabled={disabled}
				rightSection={
					loading ? (
						<Loader size="xs" />
					) : text.trim() && !disabled ? (
						<ActionIcon
							variant="transparent"
							color="gray"
							size="sm"
							onClick={() => {
								setText("");
								setOpen(false);
								onChange({ jk_id: undefined, jk_name: undefined });
							}}
						>
							<IconX size={14} />
						</ActionIcon>
					) : null
				}
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
							key={item.id}
							onClick={() => handlePick(item)}
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
							{(item.region || item.district) && (
								<Text size="xs" c="dimmed">
									{[item.region, item.district].filter(Boolean).join(" · ")}
								</Text>
							)}
						</Box>
					))}
				</Paper>
			)}
		</Box>
	);
}
