/**
 * Block F V2.0 (F1) — Stage 2: preview + optional AI description.
 *
 * Shows the listing exactly as buyers will see it (interactive ListingSlideContent
 * in a "screenshot frame"). AI description is opt-in: seller clicks
 * "Сгенерировать с AI" to start polling. "Опубликовать" is always active —
 * seller can publish with or without an AI-generated description.
 */

import { useEffect, useRef, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useUnit } from "effector-react";
import {
	Alert,
	Badge,
	Box,
	Button,
	Container,
	Group,
	Loader,
	Stack,
	Tabs,
	Text,
	Textarea,
	ThemeIcon,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
	IconArrowLeft,
	IconBulb,
	IconCheck,
	IconInfoCircle,
	IconRefresh,
	IconRobot,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import { InnerPage } from "@shared/ui/InnerPage";
import { useTelegram } from "@app/providers/useTelegram";
import { apiClient } from "@shared/api/client";
import {
	fetchDraftPreviewFx,
	publishDraftFx,
	regenerateDraftFx,
	type ListingCreateData,
} from "@shared/state/listing/model";
import type { UnifiedListing } from "@shared/api/types";
import { FeedbackLink } from "@modules/seller/feature/ai-feedback";
import { SynonymHints } from "@modules/seller/feature/synonym-hints";
import { clearDraft } from "@modules/seller/feature/listing-form/ui/listingDraftStorage";
import { ListingSlideContent } from "@modules/buyer/pages/listing-detail/ui/main/ListingSlideContent";

import {
	$currentParamSnapshot,
	$draftFormData,
	$draftId,
	$draftPreview,
	$editedDescriptions,
	$isPolling,
	$isPublishing,
	$isRegenerating,
	$paramChangeBannerDismissed,
	$paramSnapshot,
	$pollingTimedOut,
} from "../../model/stores";
import {
	dismissParamChangeBanner,
	editDescription,
	pollingTimedOut,
	resetDraftFlow,
	stageBackToParams,
	startAiGeneration,
} from "../../model/events";

const POLL_INTERVAL_MS = 2000;
const POLL_MAX_ITERATIONS = 15;

type Lang = "ru" | "uz" | "uz_cyrl";

const LANG_TABS: Array<{ value: Lang; label: string }> = [
	{ value: "ru", label: "RU" },
	{ value: "uz", label: "UZ" },
	{ value: "uz_cyrl", label: "ЎЗ" },
];

function paramsDiffer(
	a: Record<string, unknown> | null,
	b: Record<string, unknown> | null,
): boolean {
	if (!a || !b) return false;
	const keys = ["type", "district", "price", "area", "rooms"] as const;
	return keys.some((k) => a[k] !== b[k]);
}

function buildPreviewListing(
	data: ListingCreateData,
	id: string,
): UnifiedListing {
	return {
		source: "main",
		id,
		type: data.type,
		property_type: data.property_type,
		price: data.price,
		currency: data.currency,
		rooms: data.rooms ?? null,
		area: data.area ?? null,
		floor: data.floor ?? null,
		total_floors: data.total_floors ?? null,
		region: data.region ?? null,
		district: data.district,
		address: data.address ?? null,
		latitude: data.latitude ?? null,
		longitude: data.longitude ?? null,
		description: null,
		raw_text: null,
		images: (data.images ?? []).map((img) => ({
			url: img.original_url,
			thumbnail: img.thumbnail_url ?? null,
		})),
		contact_phone: data.phone ?? null,
		created_at: new Date().toISOString(),
		title: null,
		views_count: 0,
		favorites_count: 0,
		comments_count: 0,
		is_favorited: false,
		is_boosted: false,
		is_highlighted: false,
		seller_id: null,
		seller_name: null,
		seller_avatar_url: null,
		seller_verified: false,
		amenities: data.amenities ?? null,
		confidence: null,
		source_url: null,
		original_language: null,
		is_translated: false,
	};
}

function Stage2() {
	const navigate = useNavigate();
	const { webApp } = useTelegram();
	const { t } = useTranslation("seller");

	const [
		draftId,
		draftFormData,
		preview,
		edits,
		isPolling,
		pollTimedOut,
		isRegenerating,
		isPublishing,
		paramSnapshot,
		currentParams,
		paramBannerDismissed,
	] = useUnit([
		$draftId,
		$draftFormData,
		$draftPreview,
		$editedDescriptions,
		$isPolling,
		$pollingTimedOut,
		$isRegenerating,
		$isPublishing,
		$paramSnapshot,
		$currentParamSnapshot,
		$paramChangeBannerDismissed,
	]);

	const [activeTab, setActiveTab] = useState<Lang>("ru");
	const pollIterations = useRef(0);
	const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

	const previewListing = useMemo((): UnifiedListing | null => {
		if (!draftFormData || !draftId) return null;
		return buildPreviewListing(draftFormData, draftId);
	}, [draftFormData, draftId]);

	// Polling loop — only runs when $isPolling is true (user opted-in)
	useEffect(() => {
		if (!isPolling || !draftId) {
			if (pollTimer.current) {
				clearTimeout(pollTimer.current);
				pollTimer.current = null;
			}
			return;
		}
		pollIterations.current = 0;

		const tick = async () => {
			if (!draftId) return;
			pollIterations.current += 1;
			try {
				const data = await fetchDraftPreviewFx(draftId);
				if (data.ai_description_ru) return;
			} catch {
				// Network blip — keep polling
			}
			if (pollIterations.current >= POLL_MAX_ITERATIONS) {
				pollingTimedOut();
				return;
			}
			pollTimer.current = setTimeout(tick, POLL_INTERVAL_MS);
		};

		pollTimer.current = setTimeout(tick, POLL_INTERVAL_MS);

		return () => {
			if (pollTimer.current) {
				clearTimeout(pollTimer.current);
				pollTimer.current = null;
			}
		};
	}, [isPolling, draftId]);

	const handleManualRefresh = () => {
		if (!draftId) return;
		void fetchDraftPreviewFx(draftId);
	};

	const handleRegenerate = async (
		trigger: "manual_retry" | "param_change",
	) => {
		if (!draftId) return;
		try {
			await regenerateDraftFx({ id: draftId, triggered_by: trigger });
			webApp?.HapticFeedback.impactOccurred("light");
		} catch {
			notifications.show({
				title: t("notifications.error"),
				message: t(
					"createListing.regenerateFailed",
					"Не удалось перегенерировать. Попробуйте ещё раз.",
				),
				color: "red",
			});
		}
	};

	const handlePublish = async () => {
		if (!draftId) return;
		const hasAi = Boolean(preview?.ai_description_ru);
		const description = hasAi
			? edits.ru.trim() || preview?.ai_description_ru || undefined
			: undefined;
		try {
			await publishDraftFx({ id: draftId, description });
			webApp?.HapticFeedback.notificationOccurred("success");
			notifications.show({
				title: t("notifications.success"),
				message: t("notifications.listingCreated"),
				color: "green",
			});
			try {
				const res = await apiClient.get<{
					total_active_listings?: number;
					free_listings_per_seller?: number;
					test_period_active?: boolean;
				}>("/sellers/me/dashboard");
				const active = res.data.total_active_listings ?? 0;
				const free = res.data.free_listings_per_seller ?? 0;
				if (active >= 3) {
					notifications.show({
						title: t("notifications.info", "Подождите"),
						message: res.data.test_period_active
							? t("myListings.thirdListingToast", {
									count: active,
									defaultValue:
										"Это ваше {{count}}-е объявление в тестовый период",
								})
							: t("myListings.overFreeLimitToast", {
									count: active,
									free,
									defaultValue:
										"Активных объявлений: {{count}} / {{free}} бесплатных",
								}),
						color: "blue",
						autoClose: 5000,
					});
				}
			} catch {
				/* non-fatal */
			}
			resetDraftFlow();
			clearDraft();
			navigate("/seller/listings");
		} catch (err: unknown) {
			const status =
				(err as { response?: { status?: number } } | undefined)?.response
					?.status ?? null;
			const detail = (
				err as
					| { response?: { data?: { detail?: { error?: string } } } }
					| undefined
			)?.response?.data?.detail;
			if (status === 409 && detail?.error === "ai_generation_pending") {
				notifications.show({
					title: t("notifications.info", "Подождите"),
					message: t(
						"createListing.publishWaitingAi",
						"AI описание ещё генерируется. Попробуйте через несколько секунд.",
					),
					color: "yellow",
				});
				return;
			}
			notifications.show({
				title: t("notifications.error"),
				message: t(
					"createListing.publishFailed",
					"Не удалось опубликовать. Попробуйте ещё раз.",
				),
				color: "red",
			});
		}
	};

	const hasAi = Boolean(preview?.ai_description_ru);

	const showParamBanner =
		!paramBannerDismissed &&
		!isRegenerating &&
		preview?.ai_description_ru != null &&
		paramsDiffer(paramSnapshot, currentParams);

	return (
		<InnerPage
			title={t("createListing.previewPageTitle", "Ваше объявление")}
			noPadding
		>
			<Container px={0} pt="sm" pb={180}>
				<Stack gap="md">
					{/* Subtitle */}
					<Text size="xs" c="dimmed" ta="center" px="md">
						{t(
							"createListing.previewSubtitle",
							"Посмотрите, как будет выглядеть для покупателей",
						)}
					</Text>

					{/* ── Interactive "screenshot" preview frame ── */}
					{previewListing && (
						<Box
							mx="md"
							style={{
								height: "65vh",
								borderRadius: 20,
								overflow: "hidden",
								boxShadow:
									"0 8px 40px rgba(0,0,0,0.18), 0 2px 12px rgba(0,0,0,0.1)",
								border: "2.5px solid #fff",
								position: "relative",
							}}
						>
							<ListingSlideContent
								listing={previewListing}
								isActive={true}
								mode="buyer"
							/>
						</Box>
					)}

					{/* ── Optional AI description section ── */}
					<Box px="md">
						{/* State: idle — user hasn't started AI yet */}
						{!hasAi && !isPolling && !pollTimedOut && (
							<Box
								style={{
									borderRadius: 16,
									border: "1.5px solid #93c5fd",
									backgroundColor: "#f8faff",
									padding: 20,
								}}
							>
								<Group gap={10} mb={12} wrap="nowrap">
									<ThemeIcon
										size={40}
										radius="xl"
										color="blue"
										variant="light"
										style={{ flexShrink: 0 }}
									>
										<IconRobot size={22} />
									</ThemeIcon>
									<Box>
										<Text fw={700} size="sm" lh={1.3}>
											{t(
												"createListing.addAiDescription",
												"Добавьте описание с AI",
											)}
										</Text>
										<Text size="xs" c="dimmed" lh={1.4}>
											{t(
												"createListing.aiRecommend",
												"Рекомендуем — обычно выходит убедительнее",
											)}
										</Text>
									</Box>
								</Group>

								<Text size="xs" c="dimmed" mb={8}>
									{t(
										"createListing.aiLanguagesLabel",
										"Текст сразу на трёх языках:",
									)}
								</Text>
								<Group gap={6} mb={16}>
									<Badge variant="light" color="blue" size="sm" radius="md">
										🇷🇺 Русский
									</Badge>
									<Badge variant="light" color="green" size="sm" radius="md">
										🇺🇿 O&apos;zbek
									</Badge>
									<Badge variant="light" color="teal" size="sm" radius="md">
										Ўзбекча
									</Badge>
								</Group>

								<Button
									fullWidth
									radius="xl"
									leftSection={<IconRobot size={16} />}
									onClick={() => startAiGeneration()}
								>
									{t(
										"createListing.generateAiButton",
										"Сгенерировать с AI",
									)}
								</Button>

								<Text size="xs" c="dimmed" ta="center" mt={8}>
									{t(
										"createListing.aiEditableHint",
										"Результат можно отредактировать",
									)}
								</Text>
							</Box>
						)}

						{/* State: polling — AI is generating */}
						{!hasAi && isPolling && !pollTimedOut && (
							<Box
								style={{
									padding: 24,
									borderRadius: 16,
									backgroundColor: "#f0f9ff",
									border: "1px solid #bae6fd",
									display: "flex",
									flexDirection: "column",
									alignItems: "center",
									gap: 12,
								}}
							>
								<ThemeIcon size={48} radius="xl" color="blue" variant="light">
									<IconRobot size={28} />
								</ThemeIcon>
								<Text fw={600} size="sm" c="#0369a1">
									{t(
										"createListing.generatingText",
										"AI готовит описание объявления…",
									)}
								</Text>
								<Loader size="sm" color="blue" />
							</Box>
						)}

						{/* State: polling timed out */}
						{!hasAi && pollTimedOut && (
							<Alert
								icon={<IconInfoCircle size={16} />}
								color="orange"
								title={t(
									"createListing.pollingTimedOutTitle",
									"Генерация занимает дольше обычного",
								)}
							>
								<Text size="sm" mb="sm">
									{t(
										"createListing.pollingTimedOutBody",
										"Текст ещё не готов. Попробуйте обновить или сгенерировать заново.",
									)}
								</Text>
								<Group gap="sm">
									<Button
										size="xs"
										variant="light"
										leftSection={<IconRefresh size={14} />}
										onClick={handleManualRefresh}
									>
										{t("createListing.pollingRetry", "Обновить")}
									</Button>
									<Button
										size="xs"
										variant="subtle"
										loading={isRegenerating}
										onClick={() => handleRegenerate("manual_retry")}
									>
										{t(
											"createListing.regenerateButton",
											"Сгенерировать заново",
										)}
									</Button>
								</Group>
							</Alert>
						)}

						{/* State: AI text ready — show editor */}
						{hasAi && (
							<Box>
								{/* Param-change banner */}
								{showParamBanner && (
									<Alert
										icon={<IconBulb size={16} />}
										color="yellow"
										title={t(
											"createListing.paramChangedTitle",
											"Параметры изменились",
										)}
										mb="sm"
									>
										<Text size="sm" mb="sm">
											{t(
												"createListing.paramChangedBody",
												"Обновить текст с учётом изменений? Ваши правки будут потеряны.",
											)}
										</Text>
										<Group gap="sm">
											<Button
												size="xs"
												color="yellow"
												loading={isRegenerating}
												onClick={() => handleRegenerate("param_change")}
											>
												{t(
													"createListing.paramChangedUpdate",
													"Обновить",
												)}
											</Button>
											<Button
												size="xs"
												variant="subtle"
												onClick={() => dismissParamChangeBanner()}
											>
												{t(
													"createListing.paramChangedKeep",
													"Оставить как есть",
												)}
											</Button>
										</Group>
									</Alert>
								)}

								{/* Language tabs + text editors */}
								<Tabs
									value={activeTab}
									onChange={(v) => v && setActiveTab(v as Lang)}
									radius="md"
									variant="pills"
									color="blue"
								>
									<Tabs.List grow>
										{LANG_TABS.map(({ value, label }) => (
											<Tabs.Tab key={value} value={value}>
												{label}
											</Tabs.Tab>
										))}
									</Tabs.List>
									{LANG_TABS.map(({ value }) => (
										<Tabs.Panel key={value} value={value} pt="sm">
											<Textarea
												value={edits[value]}
												onChange={(e) =>
													editDescription({
														lang: value,
														value: e.currentTarget.value,
													})
												}
												minRows={6}
												maxRows={12}
												autosize
												placeholder={t(
													"createListing.editPlaceholder",
													"Текст объявления…",
												)}
											/>
										</Tabs.Panel>
									))}
								</Tabs>

								{draftId && (
									<Box mt="sm">
										<SynonymHints
											listingId={draftId}
											text={edits[activeTab] || ""}
											language={activeTab}
											currentParams={
												(currentParams ?? {}) as Record<string, unknown>
											}
											onParamApply={() => {}}
										/>
									</Box>
								)}

								<Alert
									mt="sm"
									icon={<IconInfoCircle size={14} />}
									color="blue"
									variant="light"
									radius="md"
								>
									<Text size="xs" c="#0369a1">
										{t(
											"createListing.aiDisclaimer",
											"AI создал черновик описания на основе ваших параметров. Перед публикацией обязательно перечитайте текст и убедитесь, что он точно соответствует объекту.",
										)}
									</Text>
								</Alert>

								<Group justify="space-between" mt="xs">
									{draftId ? (
										<FeedbackLink listingId={draftId} />
									) : (
										<span />
									)}
									<Button
										size="xs"
										variant="subtle"
										leftSection={<IconRefresh size={14} />}
										loading={isRegenerating}
										onClick={() => handleRegenerate("manual_retry")}
									>
										{t(
											"createListing.regenerateButton",
											"Сгенерировать заново",
										)}
									</Button>
								</Group>
							</Box>
						)}
					</Box>
				</Stack>
			</Container>

			{/* ── Fixed bottom action panel ── */}
			<Box
				style={{
					position: "fixed",
					bottom: 0,
					left: 0,
					right: 0,
					paddingBottom: "env(safe-area-inset-bottom, 0px)",
					zIndex: 10001,
					pointerEvents: "none",
				}}
			>
				<Box
					style={{
						padding: "4px 12px 12px",
						maxWidth: 500,
						margin: "0 auto",
					}}
				>
					<Box
						style={{
							display: "flex",
							alignItems: "center",
							height: 56,
							pointerEvents: "auto",
							gap: "10px",
						}}
					>
						<Button
							style={{ flex: 1 }}
							h="100%"
							radius={100}
							c="#495057"
							fw={600}
							fz={14}
							leftSection={<IconArrowLeft size={16} />}
							onClick={() => stageBackToParams()}
							styles={{
								root: {
									backgroundColor: "rgba(255, 255, 255, 0.55)",
									backdropFilter: "blur(20px) saturate(180%)",
									WebkitBackdropFilter: "blur(20px) saturate(180%)",
									border: "1px solid rgba(0, 0, 0, 0.12)",
									boxShadow: "0 4px 15px rgba(0,0,0,0.08)",
								},
							}}
						>
							{t("createListing.back", "Назад")}
						</Button>
						<Button
							style={{ flex: 1.4 }}
							h="100%"
							radius={100}
							c="white"
							fw={600}
							fz={14}
							loading={isPublishing}
							leftSection={<IconCheck size={16} />}
							onClick={handlePublish}
							styles={{
								root: {
									backgroundColor: "rgba(34, 139, 230, 0.85)",
									backdropFilter: "blur(20px) saturate(180%)",
									WebkitBackdropFilter: "blur(20px) saturate(180%)",
									boxShadow: "0 4px 15px rgba(34, 139, 230, 0.4)",
									border: "1px solid rgba(255, 255, 255, 0.2)",
								},
							}}
						>
							{t("createListing.publish", "Опубликовать")}
						</Button>
					</Box>
				</Box>
			</Box>
		</InnerPage>
	);
}

export default Stage2;
