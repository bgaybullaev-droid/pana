/**
 * Shared AI-description block for the seller listing form.
 *
 * Both the create flow (Stage1) and the edit page inject the AI generation
 * UI into the Description section of <ListingFormFields/> via four slot
 * props. Keeping that markup here — instead of duplicating it per page —
 * guarantees the two screens stay pixel-identical: any tweak to the AI
 * block lands in one place and both pages pick it up.
 *
 * The block is purely presentational: every piece of state (polling flags,
 * edited text, wishes, handlers) is passed in, so it works equally with the
 * create page's Effector stores and the edit page's local React state.
 */

import type { ReactNode } from "react";
import {
	Alert,
	Badge,
	Box,
	Button,
	Group,
	Loader,
	Tabs,
	Text,
	Textarea,
} from "@mantine/core";
import { IconInfoCircle, IconRefresh, IconRobot } from "@tabler/icons-react";
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
	/** Disable the generate button (e.g. create needs minimum params first). */
	generateDisabled: boolean;
	/** Show the "fill the basics first" hint under the disabled button. */
	showDisabledHint: boolean;
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
}

/**
 * Build the four <ListingFormFields/> description slots for the AI block.
 * Spread the result into the form-fields component on each page.
 */
export function buildAiDescriptionSlots(
	p: AiDescriptionSlotsParams,
): AiDescriptionSlots {
	const beforeDescriptionContent = p.hasAi ? (
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
	) : undefined;

	const afterDescriptionContent = (
		<Box mt={8}>
			{/* Wishes field */}
			{!p.hasAi && (
				<Textarea
					placeholder={p.t(
						"createListing.aiWishesPlaceholder",
						"Укажите особенности, которые важно упомянуть…",
					)}
					value={p.wishes}
					onChange={(e) => p.onWishesChange(e.currentTarget.value)}
					minRows={1}
					maxRows={3}
					autosize
					mb={8}
					styles={{ input: { fontSize: 13 } }}
				/>
			)}

			{/* Idle: badges + generate button */}
			{!p.hasAi && !p.isPolling && !p.pollTimedOut && (
				<>
					<Group justify="space-between" align="center" mb={4}>
						<Group gap={4}>
							<Badge variant="light" color="blue" size="sm" radius="md">
								🇷🇺 RU
							</Badge>
							<Badge variant="light" color="green" size="sm" radius="md">
								🇺🇿 UZ
							</Badge>
							<Badge variant="light" color="teal" size="sm" radius="md">
								ЎЗ
							</Badge>
						</Group>
						<Button
							size="xs"
							radius="xl"
							leftSection={<IconRobot size={14} />}
							disabled={p.generateDisabled}
							loading={p.generateLoading}
							onClick={p.onGenerate}
						>
							{p.t("createListing.generateAiButton", "Сгенерировать с AI")}
						</Button>
					</Group>
					{p.showDisabledHint && (
						<Text size="xs" c="dimmed" mt={4}>
							{p.t(
								"createListing.generateDisabledHint",
								"Заполните основные параметры и добавьте фото",
							)}
						</Text>
					)}
				</>
			)}

			{/* Polling */}
			{!p.hasAi && p.isPolling && !p.pollTimedOut && (
				<Group gap={8}>
					<Loader size="xs" color="blue" />
					<Text size="xs" fw={600} c="#0369a1">
						{p.t(
							"createListing.generatingText",
							"AI готовит описание объявления…",
						)}
					</Text>
				</Group>
			)}

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
							{p.t("createListing.regenerateButton", "Сгенерировать заново")}
						</Button>
					</Group>
				</Alert>
			)}

			{/* AI ready: just regenerate link */}
			{p.hasAi && (
				<Button
					size="xs"
					variant="subtle"
					leftSection={<IconRefresh size={12} />}
					loading={p.isRegenerating}
					onClick={p.onGenerate}
					mt={4}
				>
					{p.t("createListing.regenerateButton", "Сгенерировать заново")}
				</Button>
			)}
		</Box>
	);

	return {
		beforeDescriptionContent,
		descriptionValueOverride: p.hasAi ? p.activeText : undefined,
		onDescriptionChangeOverride: p.hasAi ? p.onActiveTextChange : undefined,
		afterDescriptionContent,
	};
}
