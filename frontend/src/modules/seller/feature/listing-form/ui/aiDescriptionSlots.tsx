/**
 * Shared AI-description block for the seller listing form.
 *
 * Both the create flow (Stage1) and the edit page inject the AI generation
 * UI into the Description section of <ListingFormFields/> via slot props.
 * Keeping that markup here — instead of duplicating it per page —
 * guarantees the two screens stay pixel-identical.
 *
 * Layout is intentionally stable across states so controls never jump:
 *
 *   [banner «Составлено ИИ» + full-width language tabs]   ← only with AI text
 *   [description field (progress overlay lives inside it)]
 *   [«Пожелания для ИИ» disclosure — always in this slot]
 *   [one full-width button: «Сгенерировать…» ⇄ «Перегенерировать»]
 *
 * The block is purely presentational: every piece of state (polling flags,
 * edited text, wishes, handlers) is passed in, so it works equally with the
 * create page's Effector stores and the edit page's local React state.
 */

import { useState, type ReactNode } from "react";
import {
	Alert,
	Anchor,
	Box,
	Button,
	Collapse,
	Group,
	SegmentedControl,
	Text,
	Textarea,
} from "@mantine/core";
import {
	IconInfoCircle,
	IconRefresh,
	IconSparkles,
} from "@tabler/icons-react";
import type { TFunction } from "i18next";

export type AiLang = "ru" | "uz" | "uz_cyrl";

export const AI_LANG_TABS: Array<{ value: AiLang; label: string }> = [
	{ value: "ru", label: "RU" },
	{ value: "uz", label: "UZ" },
	{ value: "uz_cyrl", label: "ЎЗ" },
];

export interface AiDescriptionSlotsParams {
	t: TFunction;
	/** AI text exists → switch from the "generate" CTA to the editor view. */
	hasAi: boolean;
	isPolling: boolean;
	pollTimedOut: boolean;
	isRegenerating: boolean;
	/** Spinner on the primary generate button. */
	generateLoading: boolean;
	wishes: string;
	onWishesChange: (value: string) => void;
	activeTab: AiLang;
	onActiveTabChange: (lang: AiLang) => void;
	/** Edited text for the currently-active language tab. */
	activeText: string;
	onActiveTextChange: (value: string) => void;
	onGenerate: () => void;
	onManualRefresh: () => void;
}

export interface AiDescriptionSlots {
	beforeDescriptionContent?: ReactNode;
	descriptionValueOverride?: string;
	onDescriptionChangeOverride?: (value: string) => void;
	afterDescriptionContent: ReactNode;
	/** While true the description textarea renders a progress overlay. */
	descriptionLoading: boolean;
}

/**
 * «Пожелания для ИИ» disclosure. Collapsed by default; opens pre-expanded
 * when wishes were already typed. Stays available after generation so the
 * seller can refine the wishes and hit «Перегенерировать».
 */
function WishesDisclosure({
	t,
	wishes,
	onWishesChange,
}: Pick<AiDescriptionSlotsParams, "t" | "wishes" | "onWishesChange">) {
	const [open, setOpen] = useState(wishes.length > 0);
	return (
		<Box mb={8}>
			<Anchor
				component="button"
				type="button"
				size="xs"
				onClick={() => setOpen((o) => !o)}
				style={{ display: "block" }}
			>
				{open
					? t("createListing.aiWishesToggleOpened", "− Пожелания для ИИ")
					: t(
							"createListing.aiWishesToggle",
							"+ Пожелания для ИИ (необязательно)",
						)}
			</Anchor>
			<Collapse in={open} transitionDuration={180}>
				<Textarea
					mt={6}
					placeholder={t(
						"createListing.aiWishesPlaceholder",
						"Укажите особенности, которые важно упомянуть…",
					)}
					value={wishes}
					onChange={(e) => onWishesChange(e.currentTarget.value)}
					minRows={1}
					maxRows={3}
					autosize
					styles={{ input: { fontSize: 13 } }}
				/>
			</Collapse>
		</Box>
	);
}

/**
 * Build the <ListingFormFields/> description slots for the AI block.
 * Spread the result into the form-fields component on each page.
 */
export function buildAiDescriptionSlots(
	p: AiDescriptionSlotsParams,
): AiDescriptionSlots {
	const beforeDescriptionContent = p.hasAi ? (
		<Box style={{ animation: "aiFadeIn 200ms ease" }}>
			<Group gap={6} mb={8} wrap="nowrap">
				<IconSparkles
					size={14}
					color="var(--mantine-color-teal-7)"
					style={{ flexShrink: 0 }}
				/>
				<Text size="xs" c="teal.7" fw={500} lineClamp={1}>
					{p.t(
						"createListing.aiGeneratedBanner",
						"Составлено ИИ — текст можно править",
					)}
				</Text>
			</Group>
			{/* Full-width language tabs glued to the field below */}
			<SegmentedControl
				fullWidth
				size="sm"
				radius="md"
				color="green"
				mb={6}
				value={p.activeTab}
				onChange={(v) => p.onActiveTabChange(v as AiLang)}
				data={AI_LANG_TABS.map(({ value, label }) => ({ value, label }))}
			/>
		</Box>
	) : undefined;

	const afterDescriptionContent = (
		<Box mt={8}>
			<style>{`
				@keyframes aiFadeIn {
					from { opacity: 0; transform: translateY(2px); }
					to   { opacity: 1; transform: none; }
				}
			`}</style>

			{/* Wishes — same slot in every state, so nothing jumps */}
			<WishesDisclosure
				t={p.t}
				wishes={p.wishes}
				onWishesChange={p.onWishesChange}
			/>

			{/* Timed out (initial generation only) */}
			{!p.hasAi && p.pollTimedOut ? (
				<Alert
					icon={<IconInfoCircle size={16} />}
					color="orange"
					title={p.t(
						"createListing.pollingTimedOutTitle",
						"Генерация занимает дольше обычного",
					)}
				>
					<Text size="sm" mb="sm">
						{p.t(
							"createListing.pollingTimedOutBody",
							"Текст ещё не готов. Попробуйте обновить или сгенерировать заново.",
						)}
					</Text>
					<Group gap="sm">
						<Button
							size="xs"
							variant="light"
							leftSection={<IconRefresh size={14} />}
							onClick={p.onManualRefresh}
						>
							{p.t("createListing.pollingRetry", "Обновить")}
						</Button>
						<Button
							size="xs"
							variant="subtle"
							loading={p.isRegenerating}
							onClick={p.onGenerate}
						>
							{p.t("createListing.regenerateButton", "Перегенерировать")}
						</Button>
					</Group>
				</Alert>
			) : (
				<>
					{/* One full-width action in a fixed slot: primary CTA before
					    the first generation, light regenerate after it. */}
					<Box
						key={p.hasAi ? "regenerate" : "generate"}
						style={{ animation: "aiFadeIn 200ms ease" }}
					>
						{!p.hasAi ? (
							<Button
								fullWidth
								size="md"
								radius="xl"
								leftSection={<IconSparkles size={18} />}
								loading={p.generateLoading || p.isPolling}
								onClick={p.onGenerate}
							>
								{p.t(
									"createListing.generateAiButton",
									"Сгенерировать описание",
								)}
							</Button>
						) : (
							<Button
								fullWidth
								size="md"
								radius="xl"
								variant="light"
								leftSection={<IconRefresh size={16} />}
								loading={p.isRegenerating || p.isPolling}
								onClick={p.onGenerate}
							>
								{p.t("createListing.regenerateButton", "Перегенерировать")}
							</Button>
						)}
					</Box>
					{!p.hasAi && (
						<Text size="xs" c="dimmed" ta="center" mt={6}>
							{p.t(
								"createListing.aiGenerateSubtitle",
								"ИИ напишет текст по вашим параметрам — сразу на 3 языках",
							)}
						</Text>
					)}
				</>
			)}
		</Box>
	);

	return {
		beforeDescriptionContent,
		descriptionValueOverride: p.hasAi ? p.activeText : undefined,
		onDescriptionChangeOverride: p.hasAi ? p.onActiveTextChange : undefined,
		afterDescriptionContent,
		descriptionLoading: !p.hasAi && p.isPolling,
	};
}
