import { useEffect, useMemo, useRef, useState } from "react";
import { ActionIcon, Box, Paper, Text, TextInput } from "@mantine/core";
import { IconX } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { METRO_STATIONS } from "@shared/constants/metroStations";
import { matchesQuery } from "@shared/lib/searchNormalize";

export interface MetroStationAutocompleteProps {
	/** Stable station key (e.g. "chilonzor", "paxtakor"). */
	value: string | undefined;
	onChange: (key: string | undefined) => void;
	label?: string;
	placeholder?: string;
	/** When set, suggestions are pre-filtered to this district. */
	district?: string | undefined;
	disabled?: boolean;
}

const MAX_RESULTS = 20;

export function MetroStationAutocomplete({
	value,
	onChange,
	label,
	placeholder,
	district,
	disabled,
}: MetroStationAutocompleteProps) {
	const { t } = useTranslation("seller");

	const getLabel = (key: string) =>
		t(`createListing.metroStation.${key}`, key);

	const [text, setText] = useState<string>(value ? getLabel(value) : "");
	const [open, setOpen] = useState(false);
	const boxRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		setText(value ? getLabel(value) : "");
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [value]);

	useEffect(() => {
		function handleClick(e: MouseEvent) {
			if (!boxRef.current?.contains(e.target as Node)) setOpen(false);
		}
		document.addEventListener("mousedown", handleClick);
		return () => document.removeEventListener("mousedown", handleClick);
	}, []);

	const pool = useMemo(
		() =>
			district
				? METRO_STATIONS.filter((s) => s.district === district)
				: METRO_STATIONS,
		[district],
	);

	const results = useMemo(() => {
		const q = text.trim();
		if (!q) return pool.slice(0, MAX_RESULTS);
		return pool
			.filter((s) => {
				const locLabel = getLabel(s.key);
				const keyReadable = s.key.replace(/_/g, " ");
				return matchesQuery(locLabel, q) || matchesQuery(keyReadable, q);
			})
			.slice(0, MAX_RESULTS);
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [pool, text]);

	const handleChange = (raw: string) => {
		setText(raw);
		if (!raw.trim()) onChange(undefined);
		setOpen(true);
	};

	const handlePick = (key: string) => {
		setText(getLabel(key));
		setOpen(false);
		onChange(key);
	};

	return (
		<Box ref={boxRef} style={{ position: "relative" }}>
			<TextInput
				label={label}
				placeholder={placeholder}
				value={text}
				onChange={(e) => handleChange(e.currentTarget.value)}
				onFocus={() => setOpen(true)}
				disabled={disabled}
				rightSection={
					text.trim() && !disabled ? (
						<ActionIcon
							variant="transparent"
							color="gray"
							size="sm"
							onClick={() => {
								setText("");
								setOpen(false);
								onChange(undefined);
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
					{results.map((station) => (
						<Box
							key={station.key}
							onClick={() => handlePick(station.key)}
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
								{getLabel(station.key)}
							</Text>
						</Box>
					))}
				</Paper>
			)}
		</Box>
	);
}
