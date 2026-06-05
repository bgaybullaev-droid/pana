/**
 * Block F V2.0 (F1) — Stage 1 of two-step publish.
 *
 * Parameters + photos form, plus optional in-line AI description
 * generation. User can generate AI text in three languages (RU/UZ/ЎЗ),
 * edit the result, and then advance to Stage 2 (preview + publish).
 * Advancing without generating is always allowed.
 */

import { useEffect, useRef, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useUnit } from "effector-react";
import {
	Alert,
	Box,
	Button,
	Container,
	FileButton,
	Group,
	Image,
	Loader,
	LoadingOverlay,
	Progress,
	SimpleGrid,
	Stack,
	Tabs,
	Text,
	Textarea,
	Badge,
	ActionIcon,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
	IconCameraPlus,
	IconInfoCircle,
	IconRefresh,
	IconRobot,
	IconX,
} from "@tabler/icons-react";

import { InnerPage } from "@shared/ui/InnerPage";
import { useTelegram } from "@app/providers/useTelegram";
import { FormSection } from "@shared/ui/FormSection";
import {
	createDraftListingFx,
	fetchDraftPreviewFx,
	regenerateDraftFx,
	resetCreateState,
	type ListingCreateData,
} from "@shared/state/listing/model";
import { useListingForm } from "@modules/seller/feature/listing-form/ui/useListingForm";
import {
	draftDataToFormValues,
	loadDraft,
} from "@modules/seller/feature/listing-form/ui/listingDraftStorage";
import { ListingFormFields } from "@modules/seller/feature/listing-form/ui/ListingFormFields";
import { radii } from "@app/styles/theme";

import {
	$draftFormData,
	$draftId,
	$editedDescriptions,
	$isCreatingDraft,
	$isPolling,
	$isRegenerating,
	$pollingTimedOut,
} from "../../model/stores";
import {
	editDescription,
	pollingTimedOut,
	stageAdvance,
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

function Stage1() {
	const navigate = useNavigate();
	const { webApp } = useTelegram();
	const [draftId, draftFormData, isCreatingDraft, edits, isPolling, pollTimedOut, isRegenerating] =
		useUnit([
			$draftId,
			$draftFormData,
			$isCreatingDraft,
			$editedDescriptions,
			$isPolling,
			$pollingTimedOut,
			$isRegenerating,
		]);

	const photoSectionRef = useRef<HTMLDivElement>(null);
	const [imageError, setImageError] = useState(false);
	const [wishes, setWishes] = useState("");
	const [activeTab, setActiveTab] = useState<Lang>("ru");
	const pollIterations = useRef(0);
	const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

	// Compute pre-fill values exactly once on mount.
	// Priority: $draftFormData (Stage2 → Stage1 back) > localStorage (accidental leave).
	const [initialData] = useState(() => {
		if (draftFormData) {
			return { prefill: draftDataToFormValues(draftFormData), draftImages: [] as import("@shared/state/listing/model").ListingImageCreateData[] };
		}
		const draft = loadDraft();
		return { prefill: draft?.values ?? undefined, draftImages: draft?.images ?? [] };
	});

	const {
		form,
		images,
		isUploading,
		uploadProgress,
		regions,
		districts,
		handleRegionChange,
		handleAddImages,
		handleRemoveImage,
		handleUploadImages,
		buildListingData,
		t,
	} = useListingForm("create", initialData.prefill, initialData.draftImages);

	// Reset legacy create-state on Stage 1 leave.
	useEffect(() => {
		return () => {
			resetCreateState();
		};
	}, []);

	useEffect(() => {
		if (images.length > 0 && imageError) {
			setImageError(false);
		}
	}, [images.length, imageError]);

	// AI polling loop — runs while $isPolling is true
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

	const hasMinimumParams = useMemo(() => {
		const v = form.values;
		if (!v.type || !v.property_type || !v.district || !v.price || !v.area) {
			return false;
		}
		if (
			(v.property_type === "apartment" || v.property_type === "house") &&
			v.rooms === undefined &&
			v.listing_subtype !== "studio"
		) {
			return false;
		}
		return images.length > 0 && !isUploading;
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [
		form.values.type,
		form.values.property_type,
		form.values.district,
		form.values.price,
		form.values.area,
		form.values.rooms,
		form.values.listing_subtype,
		images.length,
		isUploading,
	]);

	const hasAi = edits.ru.length > 0;

	// Keep form.values.description in sync with the RU AI description so
	// the submit payload always has the latest edited text.
	useEffect(() => {
		if (edits.ru) {
			form.setFieldValue("description", edits.ru);
		}
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [edits.ru]);

	const handleError = () => {
		if (images.length === 0) {
			setImageError(true);
		}
	};

	const handleGenerate = async () => {
		if (draftId) {
			// Draft already exists (came back from Stage 2 or already generated)
			try {
				await regenerateDraftFx({ id: draftId, triggered_by: "manual_retry" });
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
			return;
		}

		// The backend draft endpoint requires the FULL set of structured
		// fields (floor, total_floors, market_type, condition, furniture,
		// map location, …), not just the minimum gate. Validate the whole
		// form first so we surface missing fields inline instead of 400ing.
		const { hasErrors } = form.validate();
		if (hasErrors) {
			handleError();
			notifications.show({
				title: t("notifications.error"),
				message: t(
					"createListing.fillRequiredFields",
					"Заполните все обязательные поля",
				),
				color: "red",
			});
			return;
		}

		if (images.length === 0) {
			setImageError(true);
			photoSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
			return;
		}

		const uploadedImages = await handleUploadImages();
		if (uploadedImages.length === 0) {
			// Upload failed (e.g. 401) — error toast already shown by handleUploadImages
			return;
		}
		const listingData: ListingCreateData = {
			...buildListingData(form.values),
			images: uploadedImages,
		};

		try {
			await createDraftListingFx(listingData);
			startAiGeneration();
			webApp?.HapticFeedback.impactOccurred("light");
		} catch (err: unknown) {
			const message =
				err && typeof err === "object" && "message" in err
					? String((err as { message: unknown }).message)
					: t("notifications.error");
			notifications.show({
				title: t("notifications.error"),
				message,
				color: "red",
			});
		}
	};

	const handleManualRefresh = () => {
		if (!draftId) return;
		void fetchDraftPreviewFx(draftId);
	};

	const handleSubmit = async (values: typeof form.values) => {
		if (images.length === 0) {
			setImageError(true);
			photoSectionRef.current?.scrollIntoView({
				behavior: "smooth",
				block: "start",
			});
			return;
		}

		const uploadedImages = await handleUploadImages();
		if (uploadedImages.length === 0) {
			return;
		}

		const listingData: ListingCreateData = {
			...buildListingData(values),
			images: uploadedImages,
		};

		try {
			await createDraftListingFx(listingData);
			webApp?.HapticFeedback.notificationOccurred("success");
			stageAdvance();
		} catch (err: unknown) {
			const message =
				err && typeof err === "object" && "message" in err
					? String((err as { message: unknown }).message)
					: t("notifications.error");
			notifications.show({
				title: t("notifications.error"),
				message,
				color: "red",
			});
		}
	};

	const errorCount =
		Object.keys(form.errors).length +
		(images.length === 0 && imageError ? 1 : 0);

	const generateButtonStyle = {
		root: {
			backgroundColor: hasMinimumParams
				? "rgba(34, 139, 230, 1)"
				: "rgba(34, 139, 230, 0.45)",
			backdropFilter: "blur(20px) saturate(180%)",
			WebkitBackdropFilter: "blur(20px) saturate(180%)",
			boxShadow: hasMinimumParams
				? "0 4px 15px rgba(34, 139, 230, 0.45)"
				: "0 2px 8px rgba(34, 139, 230, 0.15)",
			border: "1px solid rgba(255, 255, 255, 0.2)",
			animation: hasMinimumParams ? "f1Pulse 1.4s ease-out 1" : "none",
		},
	};

	return (
		<InnerPage title={t("createListing.title")} noPadding>
			<style>{`
				@keyframes f1Pulse {
					0%   { transform: scale(1); }
					50%  { transform: scale(1.04); }
					100% { transform: scale(1); }
				}
			`}</style>
			<Container px="md" pt="md" pb={80}>
				<LoadingOverlay visible={isCreatingDraft && !isPolling} />
				<form onSubmit={form.onSubmit(handleSubmit, handleError)}>
					<Stack gap="md">
						{/* Section: Photos */}
						<div ref={photoSectionRef}>
							<FormSection title={t("createListing.photos")} required>
								{isUploading && (
									<Box mb="md">
										<Group justify="space-between" mb={4}>
											<Text size="12px" c="dimmed">
												{t("createListing.uploadingPhotos")}
											</Text>
											<Text size="12px" fw={600} c="blue">
												{uploadProgress}%
											</Text>
										</Group>
										<Progress
											value={uploadProgress}
											size="sm"
											radius="xl"
											color="blue"
											animated
										/>
									</Box>
								)}

								{images.length === 0 ? (
									<FileButton
										onChange={handleAddImages}
										accept="image/*"
										multiple
									>
										{(props) => (
											<Box
												{...props}
												style={{
													height: 100,
													borderRadius: radii.md,
													border: imageError ? "2px dashed #fca5a5" : "2px dashed #bae6fd",
													backgroundColor: imageError ? "#fff5f5" : "#f0f9ff",
													display: "flex",
													flexDirection: "column",
													alignItems: "center",
													justifyContent: "center",
													cursor: "pointer",
													gap: 4,
													transition: "all 0.2s ease",
												}}
											>
												<IconCameraPlus
													size={28}
													color={imageError ? "#f87171" : "#38bdf8"}
													stroke={1.5}
												/>
												<Text size="13px" fw={600} c={imageError ? "red.5" : "blue.6"}>
													{t("createListing.addPhotos")}
												</Text>
												<Text size="11px" c="dimmed">
													{t("createListing.upTo10")}
												</Text>
											</Box>
										)}
									</FileButton>
								) : (
									<Box>
										<Group justify="space-between" mb={8}>
											<Text size="12px" c="dimmed" fw={500}>
												{t("createListing.photosAdded")}
											</Text>
											<Badge size="sm" variant="light" color="blue" radius="sm">
												{images.length}/10
											</Badge>
										</Group>
										<SimpleGrid cols={3} spacing="xs">
											{images.map((item, index) => (
												<Box
													key={index}
													style={{
														position: "relative",
														borderRadius: radii.sm,
														overflow: "hidden",
														aspectRatio: "1",
													}}
												>
													{item.kind === "pending" && (
														<Box style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", backgroundColor: "rgba(0,0,0,0.35)", zIndex: 1 }}>
															<Loader size="xs" color="white" />
														</Box>
													)}
													<Image
														src={item.kind === "uploaded" ? item.data.thumbnail_url : item.previewUrl}
														alt={`photo-${index}`}
														fit="cover"
														style={{ width: "100%", height: "100%" }}
													/>
													<ActionIcon
														variant="filled"
														color="dark"
														radius="xl"
														size="sm"
														style={{
															position: "absolute",
															top: 4,
															right: 4,
															backgroundColor: "rgba(0,0,0,0.55)",
														}}
														onClick={(e) => {
															e.stopPropagation();
															handleRemoveImage(index);
														}}
													>
														<IconX size={12} stroke={2.5} color="white" />
													</ActionIcon>
												</Box>
											))}
											{images.length < 10 && (
												<FileButton
													onChange={(files) => {
														if (files) handleAddImages(files);
													}}
													accept="image/*"
													multiple
												>
													{(props) => (
														<Box
															{...props}
															style={{
																borderRadius: radii.sm,
																border: "2px dashed #bae6fd",
																backgroundColor: "#f0f9ff",
																aspectRatio: "1",
																display: "flex",
																alignItems: "center",
																justifyContent: "center",
																cursor: "pointer",
															}}
														>
															<IconCameraPlus
																size={22}
																color="#38bdf8"
																stroke={1.5}
															/>
														</Box>
													)}
												</FileButton>
											)}
										</SimpleGrid>
										{imageError && (
											<Text size="xs" c="red.7" mt={6}>
												{t("createListing.photosRequired")}
											</Text>
										)}
									</Box>
								)}
							</FormSection>
						</div>

						{/* Shared form fields + AI block injected into Description section */}
						<ListingFormFields
							form={form}
							regions={regions}
							districts={districts}
							onRegionChange={handleRegionChange}
							beforeDescriptionContent={
								hasAi ? (
									<Tabs
										value={activeTab}
										onChange={(v) => v && setActiveTab(v as Lang)}
										variant="pills"
										radius="md"
										color="green"
										mb={6}
									>
										<Tabs.List>
											{LANG_TABS.map(({ value, label }) => (
												<Tabs.Tab key={value} value={value}>
													{label}
												</Tabs.Tab>
											))}
										</Tabs.List>
									</Tabs>
								) : undefined
							}
							descriptionValueOverride={hasAi ? edits[activeTab] : undefined}
							onDescriptionChangeOverride={
								hasAi
									? (val) => editDescription({ lang: activeTab, value: val })
									: undefined
							}
							afterDescriptionContent={
								<Box mt={8}>
									{/* Wishes field */}
									{!hasAi && (
										<Textarea
											placeholder={t(
												"createListing.aiWishesPlaceholder",
												"Укажите особенности, которые важно упомянуть…",
											)}
											value={wishes}
											onChange={(e) => setWishes(e.currentTarget.value)}
											minRows={1}
											maxRows={3}
											autosize
											mb={8}
											styles={{ input: { fontSize: 13 } }}
										/>
									)}

									{/* Idle: badges + generate button */}
									{!hasAi && !isPolling && !pollTimedOut && (
										<>
											<Group justify="space-between" align="center" mb={4}>
												<Group gap={4}>
													<Badge variant="light" color="blue" size="sm" radius="md">🇷🇺 RU</Badge>
													<Badge variant="light" color="green" size="sm" radius="md">🇺🇿 UZ</Badge>
													<Badge variant="light" color="teal" size="sm" radius="md">ЎЗ</Badge>
												</Group>
												<Button
													size="xs"
													radius="xl"
													leftSection={<IconRobot size={14} />}
													disabled={!hasMinimumParams}
													loading={isCreatingDraft && !isPolling}
													onClick={handleGenerate}
												>
													{t("createListing.generateAiButton", "Сгенерировать с AI")}
												</Button>
											</Group>
											{!hasMinimumParams && (
												<Text size="xs" c="dimmed" mt={4}>
													{t(
														"createListing.generateDisabledHint",
														"Заполните основные параметры и добавьте фото",
													)}
												</Text>
											)}
										</>
									)}

									{/* Polling */}
									{!hasAi && isPolling && !pollTimedOut && (
										<Group gap={8}>
											<Loader size="xs" color="blue" />
											<Text size="xs" fw={600} c="#0369a1">
												{t(
													"createListing.generatingText",
													"AI готовит описание объявления…",
												)}
											</Text>
										</Group>
									)}

									{/* Timed out */}
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
													onClick={handleGenerate}
												>
													{t("createListing.regenerateButton", "Сгенерировать заново")}
												</Button>
											</Group>
										</Alert>
									)}

									{/* AI ready: just regenerate link */}
									{hasAi && (
										<Button
											size="xs"
											variant="subtle"
											leftSection={<IconRefresh size={12} />}
											loading={isRegenerating}
											onClick={handleGenerate}
											mt={4}
										>
											{t("createListing.regenerateButton", "Сгенерировать заново")}
										</Button>
									)}
								</Box>
							}
						/>

					</Stack>
				</form>

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
						{errorCount > 0 && (
							<Box
								style={{
									backgroundColor: "#fee2e2",
									border: "1px solid #fca5a5",
									padding: "10px 16px",
									borderRadius: 20,
									marginBottom: 12,
									pointerEvents: "auto",
									boxShadow: "0 4px 12px rgba(0,0,0,0.05)",
								}}
							>
								<Text size="xs" c="red.8" fw={500} ta="center">
									{t("createListing.unfilledFieldsSummary", {
										count: errorCount,
									})}
								</Text>
							</Box>
						)}
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
								onClick={() => navigate(-1)}
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
								{t("createListing.cancel")}
							</Button>
							<Button
								style={{ flex: 1 }}
								h="100%"
								radius={100}
								c="white"
								fw={600}
								fz={14}
								disabled={!hasMinimumParams}
								loading={(isCreatingDraft && !isPolling) || isUploading}
								onClick={() => {
									if (draftId) {
										stageAdvance();
									} else {
										form.onSubmit(handleSubmit, handleError)();
									}
								}}
								styles={generateButtonStyle}
							>
								{isUploading
									? t("createListing.uploadingPhotos")
									: t("createListing.nextButton", "Далее →")}
							</Button>
						</Box>
						{!hasMinimumParams && (
							<Text
								size="11px"
								c="dimmed"
								ta="center"
								mt={6}
								style={{ pointerEvents: "auto" }}
							>
								{t(
									"createListing.generateDisabledHint",
									"Заполните основные параметры и добавьте фото",
								)}
							</Text>
						)}
					</Box>
				</Box>
			</Container>
		</InnerPage>
	);
}

export default Stage1;
