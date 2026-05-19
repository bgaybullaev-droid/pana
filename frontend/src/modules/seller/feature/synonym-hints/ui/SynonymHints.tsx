/**
 * Block F V2.0 (F2) — Stage 2 synonym hint cards.
 *
 * Polls ``POST /listings/{id}/analyse-text`` with a 1s debounce after
 * each text edit, then renders one of two card variants per match:
 *
 *   - ``action="add"``       (blue): "Кажется, вы упомянули X. Добавить
 *     в параметры?"  → buttons Yes / Keep.
 *   - ``action="contradict"`` (orange): "Параметры говорят одно, текст —
 *     другое."  → Change / Fix-text / Keep.
 *
 * When 3+ matches come back, fold into a single grouped card with an
 * expandable list and a "Добавить все" bulk button (positive matches
 * only — contradictions stay individual so the seller stays in control).
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { useUnit } from "effector-react";
import { Alert, Button, Group, Stack, Text, Collapse } from "@mantine/core";
import {
	IconBulb,
	IconAlertTriangle,
	IconChevronDown,
	IconChevronUp,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import {
	$dismissedKeys,
	analyseTextFx,
	matchDismissed,
	type SynonymMatch,
} from "../model";

interface SynonymHintsProps {
	listingId: string;
	text: string;
	language: string;
	currentParams: Record<string, unknown>;
	/** Fired with `{ key, value }` when seller clicks "add" / "change param". */
	onParamApply: (key: string, value: string | boolean) => void;
}

const _DEBOUNCE_MS = 1000;
const _GROUP_THRESHOLD = 3;

export function SynonymHints({
	listingId,
	text,
	language,
	currentParams,
	onParamApply,
}: SynonymHintsProps) {
	const { t } = useTranslation("seller");
	const [matches, setMatches] = useState<SynonymMatch[]>([]);
	const [groupExpanded, setGroupExpanded] = useState(false);
	const dismissedKeys = useUnit($dismissedKeys);
	const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
	const abortRef = useRef<AbortController | null>(null);

	useEffect(() => {
		// Clear any pending timer; only the latest edit wins.
		if (debounceTimer.current) {
			clearTimeout(debounceTimer.current);
			debounceTimer.current = null;
		}
		if (!text || text.trim().length < 5) {
			setMatches([]);
			return;
		}
		debounceTimer.current = setTimeout(async () => {
			// Cancel any in-flight previous request so only the latest
			// finishes. Effector effects don't take an AbortSignal so we
			// drop the response if a new run starts before this one ends.
			const myController = new AbortController();
			abortRef.current?.abort();
			abortRef.current = myController;
			try {
				const result = await analyseTextFx({
					listingId,
					text,
					language,
					currentParams,
				});
				if (!myController.signal.aborted) {
					setMatches(result);
				}
			} catch {
				// Silent — synonym hints are an optional UX layer, never
				// surface a toast when the backend hiccups.
			}
		}, _DEBOUNCE_MS);

		return () => {
			if (debounceTimer.current) {
				clearTimeout(debounceTimer.current);
				debounceTimer.current = null;
			}
		};
	}, [text, language, listingId, JSON.stringify(currentParams)]);

	const visible = useMemo(
		() =>
			matches.filter((m) => !dismissedKeys.has(`${m.parameter_key}|${m.action}`)),
		[matches, dismissedKeys],
	);

	if (visible.length === 0) {
		return null;
	}

	const dismissKey = (m: SynonymMatch) =>
		matchDismissed(`${m.parameter_key}|${m.action}`);

	const handleApply = (m: SynonymMatch) => {
		if (m.parameter_value !== null) {
			onParamApply(m.parameter_key, m.parameter_value);
		} else {
			onParamApply(m.parameter_key, m.polarity === "positive");
		}
		dismissKey(m);
	};

	const handleApplyAll = () => {
		for (const m of visible) {
			if (m.action !== "add") continue;
			handleApply(m);
		}
	};

	if (visible.length >= _GROUP_THRESHOLD) {
		const addCount = visible.filter((m) => m.action === "add").length;
		return (
			<Alert
				icon={<IconBulb size={16} />}
				color="blue"
				variant="light"
				title={t(
					"synonymHints.groupTitle",
					"Найдено {{count}} упоминаний параметров",
					{ count: visible.length },
				)}
			>
				<Stack gap={6}>
					<Group gap="xs">
						{addCount > 0 && (
							<Button size="xs" color="blue" onClick={handleApplyAll}>
								{t("synonymHints.applyAll", "Добавить все")}
							</Button>
						)}
						<Button
							size="xs"
							variant="subtle"
							leftSection={
								groupExpanded ? <IconChevronUp size={12} /> : <IconChevronDown size={12} />
							}
							onClick={() => setGroupExpanded((v) => !v)}
						>
							{groupExpanded
								? t("synonymHints.collapse", "Свернуть")
								: t("synonymHints.expand", "Показать все")}
						</Button>
					</Group>
					<Collapse in={groupExpanded}>
						<Stack gap={6}>
							{visible.map((m) => (
								<SingleHint
									key={`${m.parameter_key}-${m.action}-${m.position}`}
									match={m}
									onApply={() => handleApply(m)}
									onDismiss={() => dismissKey(m)}
									compact
								/>
							))}
						</Stack>
					</Collapse>
				</Stack>
			</Alert>
		);
	}

	return (
		<Stack gap={6}>
			{visible.map((m) => (
				<SingleHint
					key={`${m.parameter_key}-${m.action}-${m.position}`}
					match={m}
					onApply={() => handleApply(m)}
					onDismiss={() => dismissKey(m)}
				/>
			))}
		</Stack>
	);
}

interface SingleHintProps {
	match: SynonymMatch;
	onApply: () => void;
	onDismiss: () => void;
	compact?: boolean;
}

function SingleHint({ match, onApply, onDismiss, compact }: SingleHintProps) {
	const { t } = useTranslation("seller");
	const isAdd = match.action === "add";
	const color = isAdd ? "blue" : "orange";
	const icon = isAdd ? <IconBulb size={14} /> : <IconAlertTriangle size={14} />;
	const titleKey = isAdd ? "synonymHints.addTitle" : "synonymHints.contradictTitle";
	const defaultTitle = isAdd
		? "Кажется, вы упомянули «{{form}}». Добавить в параметры?"
		: "В параметрах указано одно, в тексте — другое: «{{form}}».";

	return (
		<Alert
			icon={icon}
			color={color}
			variant={compact ? "light" : "filled"}
			styles={compact ? undefined : { root: { padding: 10 } }}
		>
			<Text size="13px" mb={6}>
				{t(titleKey, defaultTitle, { form: match.surface_form })}
			</Text>
			<Group gap="xs">
				<Button size="xs" color={color} onClick={onApply}>
					{isAdd
						? t("synonymHints.applyAdd", "Да, добавить")
						: t("synonymHints.applyChange", "Изменить параметр")}
				</Button>
				<Button size="xs" variant="subtle" onClick={onDismiss}>
					{t("synonymHints.keep", "Оставить как есть")}
				</Button>
			</Group>
		</Alert>
	);
}
