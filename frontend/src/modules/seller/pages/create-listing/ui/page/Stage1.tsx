/**
 * Block F V2.0 (F1) — Stage 1 of two-step publish.
 *
 * Parameters + photos form, plus optional in-line AI description
 * generation. User can generate AI text in three languages (RU/UZ/ЎЗ),
 * edit the result, and then advance to Stage 2 (preview + publish).
 * Advancing without generating is always allowed.
 */

import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useUnit } from "effector-react";
import {
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
	Text,
	Badge,
	ActionIcon,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
	IconCameraPlus,
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
import { useListingCompleteness } from "@modules/seller/feature/listing-form/ui/useListingCompleteness";
import { RequiredProgressRing } from "@modules/seller/feature/listing-form/ui/RequiredProgressRing";
import { scrollToSection } from "@modules/seller/feature/listing-form/lib/scrollToSection";
import {
	buildAiDescriptionSlots,
	type AiLang,
} from "@modules/seller/feature/listing-form/ui/aiDescriptionSlots";
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
	const [activeTab, setActiveTab] = useState<AiLang>("ru");
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

	const [submitAttempted, setSubmitAttempted] = useState(false);
	const { sectionStates, progress, isComplete, firstIncompleteSection } =
		useListingCompleteness({
			values: form.values,
			mode: "create",
			imageCount: images.length,
			submitAttempted,
		});
	const readyToProceed = isComplete && !isUploading;

	// Any language having text keeps the AI editor (tabs) open — clearing
	// all three via the field's ✕ returns the block to the generate CTA.
	const hasAi =
		edits.ru.length > 0 || edits.uz.length > 0 || edits.uz_cyrl.length > 0;

	// Keep form.values.description in sync with the RU AI description so
	// the submit payload always has the latest edited text. Also syncs the
	// non-empty → empty transition (✕ clear), but not the initial "" so a
	// restored draft description isn't wiped on mount.
	const prevEditsRu = useRef("");
	useEffect(() => {
		if (edits.ru || prevEditsRu.current) {
			form.setFieldValue("description", edits.ru);
		}
		prevEditsRu.current = edits.ru;
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [edits.ru]);

	const handleError = () => {
		if (images.length === 0) {
			setImageError(true);
		}
		// Paint incomplete sections red and lead the user to the first one.
		setSubmitAttempted(true);
		if (firstIncompleteSection) {
			scrollToSection(firstIncompleteSection);
		}
	};

	const handleGenerate = async () => {
		if (draftId) {
			// Draft already exists (came back from Stage 2 or already generated)
			try {
				await regenerateDraftFx({
					id: draftId,
					triggered_by: "manual_retry",
					wishes: wishes.trim() || undefined,
				});
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
			setSubmitAttempted(true);
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
			ai_wishes: wishes.trim() || undefined,
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
			setSubmitAttempted(true);
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
			ai_wishes: wishes.trim() || undefined,
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

	const generateButtonStyle = {
		root: {
			backgroundColor: readyToProceed
				? "rgba(34, 139, 230, 1)"
				: "rgba(34, 139, 230, 0.45)",
			backdropFilter: "blur(20px) saturate(180%)",
			WebkitBackdropFilter: "blur(20px) saturate(180%)",
			boxShadow: readyToProceed
				? "0 4px 15px rgba(34, 139, 230, 0.45)"
				: "0 2px 8px rgba(34, 139, 230, 0.15)",
			border: "1px solid rgba(255, 255, 255, 0.2)",
			animation: readyToProceed ? "f1Pulse 1.4s ease-out 1" : "none",
		},
	};

	// Photos section status — same labels ListingFormFields uses internally.
	const photosState = sectionStates.photos;
	const photosStatusProps =
		photosState.status === "complete"
			? {
					status: "complete" as const,
					statusLabel: t("createListing.sectionComplete"),
				}
			: photosState.status === "error"
				? {
						status: "error" as const,
						statusLabel: t("createListing.sectionRemaining", {
							count: photosState.remaining,
						}),
					}
				: { status: "neutral" as const };

	// Shared AI-description block — same source on the edit page. The CTA
	// stays enabled even on an incomplete form: handleGenerate validates,
	// paints incomplete sections red and scrolls to the first one.
	const aiSlots = buildAiDescriptionSlots({
		t,
		hasAi,
		isPolling,
		pollTimedOut,
		isRegenerating,
		generateLoading: (isCreatingDraft && !isPolling) || isUploading,
		wishes,
		onWishesChange: setWishes,
		activeTab,
		onActiveTabChange: setActiveTab,
		activeText: edits[activeTab],
		onActiveTextChange: (val) => editDescription({ lang: activeTab, value: val }),
		onGenerate: handleGenerate,
		onManualRefresh: handleManualRefresh,
	});

	return (
		<InnerPage title={t("createListing.title")} noPadding>
			<style>{`
				@keyframes f1Pulse {
					0%   { transform: scale(1); }
					50%  { transform: scale(1.04); }
					100% { transform: scale(1); }
				}
				@keyframes ctaSwap {
					from { opacity: 0; transform: translateY(2px); }
					to   { opacity: 1; transform: none; }
				}
			`}</style>
			<Container px="md" pt="md" pb={80}>
				<LoadingOverlay visible={isCreatingDraft && !isPolling} />
				<form onSubmit={form.onSubmit(handleSubmit, handleError)}>
					<Stack gap="md">
						{/* Section: Photos */}
						<div
							ref={photoSectionRef}
							data-section-key="photos"
							style={{ scrollMarginTop: 12 }}
						>
							<FormSection
								title={t("createListing.photos")}
								required
								{...photosStatusProps}
							>
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
							sectionStates={sectionStates}
							beforeDescriptionContent={aiSlots.beforeDescriptionContent}
							descriptionValueOverride={aiSlots.descriptionValueOverride}
							onDescriptionChangeOverride={aiSlots.onDescriptionChangeOverride}
							afterDescriptionContent={aiSlots.afterDescriptionContent}
							descriptionLoading={aiSlots.descriptionLoading}
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
						paddingBottom: "var(--safe-area-inset-bottom)",
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
								loading={(isCreatingDraft && !isPolling) || isUploading}
								onClick={() => {
									// Not disabled on purpose: a click on the muted button
									// validates, paints incomplete sections red and scrolls
									// to the first one instead of silently doing nothing.
									if (!readyToProceed) {
										if (isUploading) return;
										setSubmitAttempted(true);
										form.validate();
										if (images.length === 0) setImageError(true);
										if (firstIncompleteSection) {
											scrollToSection(firstIncompleteSection);
										}
										return;
									}
									if (draftId) {
										stageAdvance();
									} else {
										form.onSubmit(handleSubmit, handleError)();
									}
								}}
								styles={generateButtonStyle}
							>
								{/* Smart CTA: while required fields remain, the button
								    itself shows a mini progress ring + «Ещё N полей»
								    (tap still validates + scrolls to the first gap);
								    once complete it morphs into «Далее →». */}
								{isUploading ? (
									t("createListing.uploadingPhotos")
								) : readyToProceed ? (
									<span
										key="cta-ready"
										style={{ animation: "ctaSwap 200ms ease" }}
									>
										{t("createListing.nextButton", "Далее →")}
									</span>
								) : (
									<span
										key="cta-remaining"
										style={{
											display: "inline-flex",
											alignItems: "center",
											gap: 8,
											animation: "ctaSwap 200ms ease",
										}}
									>
										<RequiredProgressRing
											filled={progress.filled}
											total={progress.total}
										/>
										{t("createListing.ctaRemaining", {
											count: progress.total - progress.filled,
										})}
									</span>
								)}
							</Button>
						</Box>
					</Box>
				</Box>
			</Container>
		</InnerPage>
	);
}

export default Stage1;
