/**
 * Shared AI-description block for the seller listing form.
 *
 * Both the create flow (Stage1) and the edit page inject the AI generation
 * UI into the Description section of <ListingFormFields/> via slot props.
 * Keeping that markup here — instead of duplicating it per page —
 * guarantees the two screens stay pixel-identical: any tweak to the AI
 * block lands in one place and both pages pick it up.
 *
 * UX follows the industry "AI inside the field" pattern (Avito/Notion/
 * LinkedIn): one familiar textarea, one prominent CTA below it, generation
 * progress rendered inside the field itself (descriptionLoading slot), and
 * the result landing in the same field. Wishes are collapsed behind a
 * disclosure link; language chips appear only after generation.
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
	Group,
	Tabs,
	Text,
	Textarea,
} from "@mantine/core";
import {
	IconInfoCircle,
	IconPencil,
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
	/** Drop the AI texts and hand the field back to manual writing. */
	onResetToManual: () => void;
}

export interface AiDescriptionSlots {
	beforeDescriptionContent?: ReactNode;
	descriptionValueOverride?: string;
	onDescriptionChangeOverride?: (value: string) => void;
	afterDescriptionContent: ReactNode;
	/** While true the description textarea renders a skeleton overlay. */
	descriptionLoading: boolean;
}

/**
 * Optional wishes input, collapsed behind a disclosure link so the default
 * view stays a single field + single CTA. Opens pre-expanded when wishes
 * were already typed (e.g. coming back from Stage 2).
 */
function WishesDisclosure({
	t,
	wishes,
	onWishesChange,
}: Pick<AiDescriptionSlotsParams, "t" | "wishes" | "onWishesChange">) {
	const [open, setOpen] = useState(wishes.length > 0);
	if (!open) {
		return (
			<Anchor
				component="button"
				type="button"
				size="xs"
				onClick={() => setOpen(true)}
				style={{ display: "block", marginBottom: 8 }}
			>
				{t("createListing.aiWishesToggle", "+ Пожелания для ИИ (необязательно)")}
			</Anchor>
		);
	}
	return (
		<Textarea
			placeholder={t(
				"createListing.aiWishesPlaceholder",
				"Укажите особенности, которые важно упомянуть…",
			)}
			value={wishes}
			onChange={(e) => onWishesChange(e.currentTarget.value)}
			minRows={1}
			maxRows={3}
			autosize
			mb={8}
			styles={{ input: { fontSize: 13 } }}
		/>
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
		<>
			<Tabs
				value={p.activeTab}
				onChange={(v) => v && p.onActiveTabChange(v as AiLang)}
				variant="pills"
				radius="md"
				color="green"
				mb={6}
			>
				<Tabs.List>
					{AI_LANG_TABS.map(({ value, label }) => (
						<Tabs.Tab key={value} value={value}>
							{label}
						</Tabs.Tab>
					))}
				</Tabs.List>
			</Tabs>
			<Group gap={6} mb={6} wrap="nowrap">
				<IconSparkles size={14} color="var(--mantine-color-teal-7)" />
				<Text size="xs" c="teal.7" fw={500}>
					{p.t(
						"createListing.aiGeneratedBanner",
						"Текст составлен ИИ — отредактируйте при необходимости",
					)}
				</Text>
			</Group>
		</>
	) : undefined;

	const afterDescriptionContent = (
		<Box mt={8}>
			{/* Idle: collapsed wishes + one prominent CTA */}
			{!p.hasAi && !p.isPolling && !p.pollTimedOut && (
				<>
					<WishesDisclosure
						t={p.t}
						wishes={p.wishes}
						onWishesChange={p.onWishesChange}
					/>
					<Button
						fullWidth
						size="md"
						radius="xl"
						leftSection={<IconSparkles size={18} />}
						loading={p.generateLoading}
						onClick={p.onGenerate}
					>
						{p.t("createListing.generateAiButton", "Сгенерировать описание")}
					</Button>
					<Text size="xs" c="dimmed" ta="center" mt={6}>
						{p.t(
							"createListing.aiGenerateSubtitle",
							"ИИ напишет текст по вашим параметрам — сразу на 3 языках",
						)}
					</Text>
				</>
			)}

			{/* Polling progress renders inside the field itself
			    (descriptionLoading overlay) — nothing extra below. */}

			{/* Timed out */}
			{!p.hasAi && p.pollTimedOut && (
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
			)}

			{/* AI ready: regenerate or hand the field back to manual writing */}
			{p.hasAi && (
				<Group gap="sm" mt={4}>
					<Button
						size="xs"
						variant="light"
						leftSection={<IconRefresh size={12} />}
						loading={p.isRegenerating}
						onClick={p.onGenerate}
					>
						{p.t("createListing.regenerateButton", "Перегенерировать")}
					</Button>
					<Button
						size="xs"
						variant="subtle"
						color="gray"
						leftSection={<IconPencil size={12} />}
						onClick={p.onResetToManual}
					>
						{p.t("createListing.aiResetToManual", "Написать вручную")}
					</Button>
				</Group>
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
