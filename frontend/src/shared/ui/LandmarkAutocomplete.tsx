/**
 * PR-G — Landmark autocomplete for the seller listing form.
 *
 * Mirrors HousingComplexAutocomplete (dual-column jk_id/jk_name pattern):
 *   - User types → 300ms debounce → /landmarks?q=…&district=… fetch.
 *   - Picking a suggestion → onChange({ landmark_id, landmark }).
 *   - Free-text that doesn't match → onChange({ landmark_id: undefined,
 *     landmark: <text> }). Backend accepts this during the dual-column window.
 *   - Suggestions are scoped by the chosen district (район→ориентир cascade);
 *     a `region` fallback keeps results sane before a district is picked.
 *   - Network / server failure → dropdown disappears; user keeps typing
 *     in free-text mode (graceful degrade).
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { ActionIcon, Box, Loader, Paper, Text, TextInput } from "@mantine/core";
import { IconX } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import {
	landmarkName,
	searchLandmarks,
	type LandmarkListItem,
} from "@shared/api/landmarks";

export interface LandmarkSelection {
	landmark_id: string | undefined;
	landmark: string | undefined;
}

export interface LandmarkAutocompleteProps {
	value: LandmarkSelection;
	onChange: (next: LandmarkSelection) => void;
	label?: string;
	placeholder?: string;
	/** Narrow suggestions to a district slug (район→ориентир cascade). */
	district?: string | undefined;
	/** Region fallback scope, used before a district is chosen. */
	region?: string | undefined;
	disabled?: boolean;
}

const DEBOUNCE_MS = 300;
const MIN_CHARS = 1;
const MAX_RESULTS = 10;

export function LandmarkAutocomplete({
	value,
	onChange,
	label,
	placeholder,
	district,
	region,
	disabled,
}: LandmarkAutocompleteProps) {
	const { t, i18n } = useTranslation("common");
	const [text, setText] = useState<string>(value.landmark ?? "");
	const [results, setResults] = useState<LandmarkListItem[]>([]);
	const [open, setOpen] = useState(false);
	const [loading, setLoading] = useState(false);
	const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const boxRef = useRef<HTMLDivElement>(null);

	// Re-sync if the parent updates `value.landmark` externally (edit-mode).
	useEffect(() => {
		setText(value.landmark ?? "");
	}, [value.landmark]);

	// Pre-load suggestions when district changes (район→ориентир cascade).
	// The backend returns the first N results for empty q scoped to the
	// district, so the user sees options immediately on focus without typing.
	useEffect(() => {
		if (!district || text.trim()) return;
		searchLandmarks({ q: "", district, region, limit: MAX_RESULTS })
			.then((list) => setResults(list))
			.catch(() => {});
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [district, region]);

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
			const list = await searchLandmarks({
				q,
				district,
				region,
				limit: MAX_RESULTS,
			});
			setResults(list);
			setOpen(list.length > 0);
			setLoading(false);
		}, DEBOUNCE_MS);
	};

	const handleChange = (raw: string) => {
		setText(raw);
		// Typing invalidates a previously-picked landmark_id.
		onChange({ landmark_id: undefined, landmark: raw.trim() || undefined });
		scheduleSearch(raw);
	};

	const handlePick = (item: LandmarkListItem) => {
		const name = landmarkName(item, i18n.language);
		setText(name);
		setOpen(false);
		onChange({ landmark_id: item.id, landmark: name });
	};

	const description = useMemo(() => {
		if (!value.landmark_id) return undefined;
		return t("landmark.linked");
	}, [value.landmark_id, t]);

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
								onChange({ landmark_id: undefined, landmark: undefined });
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
					{results.map((item) => {
						const name = landmarkName(item, i18n.language);
						const sub = [item.category, item.microdistrict || item.district]
							.filter(Boolean)
							.join(" · ");
						return (
							<Box
								key={item.id}
								onClick={() => handlePick(item)}
								style={{ padding: "8px 12px", cursor: "pointer" }}
								onMouseEnter={(e) => {
									(e.currentTarget as HTMLElement).style.backgroundColor =
										"#f1f3f5";
								}}
								onMouseLeave={(e) => {
									(e.currentTarget as HTMLElement).style.backgroundColor = "";
								}}
							>
								<Text size="sm" fw={500}>
									{name}
								</Text>
								{sub && (
									<Text size="xs" c="dimmed">
										{sub}
									</Text>
								)}
							</Box>
						);
					})}
				</Paper>
			)}
		</Box>
	);
}
