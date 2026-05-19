/**
 * Block F V2.0 (F1) — Stage 2 of two-step publish.
 *
 * Polls /listings/{id}/draft-preview at 2s × 15 iterations (30s budget).
 * When ai_description_ru lands the textareas seed once; further polling
 * stops. Seller edits three locales independently, optionally
 * regenerates after param drift, and clicks "Опубликовать" which
 * PATCHes status=active. The backend's 409 ai_generation_pending
 * surfaces as a toast and the polling resumes.
 */

import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useUnit } from "effector-react";
import {
	Alert,
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
} from "@shared/state/listing/model";
import { FeedbackLink } from "@modules/seller/feature/ai-feedback";
import { SynonymHints } from "@modules/seller/feature/synonym-hints";

import {
	$currentParamSnapshot,
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
} from "../../model/events";

const POLL_INTERVAL_MS = 2000;
const POLL_MAX_ITERATIONS = 15; // 15 × 2s = 30s budget

type Lang = "ru" | "uz" | "uz_cyrl";

const LANG_TABS: Array<{ value: Lang; label: string }> = [
	{ value: "ru", label: "RU" },
	{ value: "uz", label: "UZ" },
	{ value: "uz_cyrl", label: "ЎЗ" },
];

/** Shallow compare of the 5 key params we track for drift detection. */
function paramsDiffer(
	a: Record<string, unknown> | null,
	b: Record<string, unknown> | null,
): boolean {
	if (!a || !b) return false;
	const keys = ["type", "district", "price", "area", "rooms"] as const;
	return keys.some((k) => a[k] !== b[k]);
}

function Stage2() {
	const navigate = useNavigate();
	const { webApp } = useTelegram();
	const { t } = useTranslation("seller");

	const [
		draftId,
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

	// ── Polling loop ─────────────────────────────────────────────────
	useEffect(() => {
		// Reset iteration counter every time we (re)start polling.
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
				if (data.ai_description_ru) {
					// Store reducer will flip $isPolling=false; the effect
					// will cleanup the timer on the next render.
					return;
				}
			} catch {
				// Network blip: keep polling until timeout. We don't want
				// to surface every transient 5xx — the manual "Обновить"
				// button is the recovery path.
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

	// Cleanup on unmount — full state reset is owned by Page.tsx wrapper
	// (so back-navigation between stages preserves edits).

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
		const description = edits.ru.trim() || preview?.ai_description_ru || "";
		try {
			await publishDraftFx({ id: draftId, description });
			webApp?.HapticFeedback.notificationOccurred("success");
			notifications.show({
				title: t("notifications.success"),
				message: t("notifications.listingCreated"),
				color: "green",
			});
			// Block C V2.0 (C2) — after a successful publish, hint that
			// the seller is approaching/over the free-listings limit during
			// the test period. Best-effort: failure to read the dashboard
			// just suppresses the hint.
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
			navigate("/seller/listings");
		} catch (err: unknown) {
			// Backend 409 ai_generation_pending → keep polling; toast a hint.
			const status =
				(err as { response?: { status?: number } } | undefined)?.response
					?.status ?? null;
			const detail =
				(
					err as
						| {
								response?: { data?: { detail?: { error?: string } } };
						  }
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

	const showParamBanner =
		!paramBannerDismissed &&
		!isRegenerating &&
		preview?.ai_description_ru != null &&
		paramsDiffer(paramSnapshot, currentParams);

	const hasAi = Boolean(preview?.ai_description_ru);

	return (
		<InnerPage title={t("createListing.previewTitle", "Просмотр объявления")} noPadding>
			<Container px="md" pt="md" pb={160}>
				<Stack gap="md">
					{/* Polling loading state */}
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

					{/* Polling timeout state */}
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
									{t("createListing.regenerateButton", "Сгенерировать заново")}
								</Button>
							</Group>
						</Alert>
					)}

					{/* Param-change banner */}
					{showParamBanner && (
						<Alert
							icon={<IconBulb size={16} />}
							color="yellow"
							title={t(
								"createListing.paramChangedTitle",
								"Параметры изменились",
							)}
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
									{t("createListing.paramChangedUpdate", "Обновить")}
								</Button>
								<Button
									size="xs"
									variant="subtle"
									onClick={() => dismissParamChangeBanner()}
								>
									{t("createListing.paramChangedKeep", "Оставить как есть")}
								</Button>
							</Group>
						</Alert>
					)}

					{/* AI text editor */}
					{hasAi && (
						<Box>
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

							{/* Block F F2 — synonym hint cards for the active tab. */}
							{draftId && (
								<Box mt="sm">
									<SynonymHints
										listingId={draftId}
										text={edits[activeTab] || ""}
										language={activeTab}
										currentParams={(currentParams ?? {}) as Record<string, unknown>}
										onParamApply={() => {
											// Stage 2 has no params editor — sellers go back to
											// Stage 1 to amend structured fields. The hint click
											// is currently best-effort UI feedback only; the
											// underlying ``currentParams`` will refresh on the
											// next Stage 1 → Stage 2 round-trip.
										}}
									/>
								</Box>
							)}

							{/* Disclaimer */}
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

							{/* Regenerate (manual) + Feedback */}
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
									{t("createListing.regenerateButton", "Сгенерировать заново")}
								</Button>
							</Group>
						</Box>
					)}
				</Stack>

				{/* Fixed Action Buttons Panel */}
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
								disabled={!hasAi}
								loading={isPublishing}
								leftSection={<IconCheck size={16} />}
								onClick={handlePublish}
								styles={{
									root: {
										backgroundColor: hasAi
											? "rgba(34, 139, 230, 0.85)"
											: "rgba(34, 139, 230, 0.35)",
										backdropFilter: "blur(20px) saturate(180%)",
										WebkitBackdropFilter: "blur(20px) saturate(180%)",
										boxShadow: hasAi
											? "0 4px 15px rgba(34, 139, 230, 0.4)"
											: "0 2px 8px rgba(34, 139, 230, 0.2)",
										border: "1px solid rgba(255, 255, 255, 0.2)",
									},
								}}
							>
								{t("createListing.publish", "Опубликовать")}
							</Button>
						</Box>
					</Box>
				</Box>
			</Container>
		</InnerPage>
	);
}

export default Stage2;
