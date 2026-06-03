/**
 * Block F V2.0 (F1) — Stage 1 of two-step publish.
 *
 * Carries the legacy parameter / photo form from before F1; the only
 * substantive change is the submit handler: instead of POST /listings
 * (which immediately publishes), Stage 1 calls
 * createDraftListingFx → POST /listings/draft. On success the parent
 * Page.tsx wrapper flips $stage to 2 and Stage2.tsx mounts.
 */

import { useEffect, useRef, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useUnit } from "effector-react";
import {
	Container,
	Stack,
	FileButton,
	Image,
	SimpleGrid,
	Box,
	ActionIcon,
	Text,
	Button,
	LoadingOverlay,
	Progress,
	Badge,
	Group,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconX, IconCameraPlus } from "@tabler/icons-react";

import { InnerPage } from "@shared/ui/InnerPage";
import { useTelegram } from "@app/providers/useTelegram";
import { FormSection } from "@shared/ui/FormSection";
import {
	createDraftListingFx,
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

import { $draftFormData, $isCreatingDraft } from "../../model/stores";
import { setCurrentParamSnapshot } from "../../model/events";

function Stage1() {
	const navigate = useNavigate();
	const { webApp } = useTelegram();
	const isCreatingDraft = useUnit($isCreatingDraft);
	const draftFormData = useUnit($draftFormData);
	const photoSectionRef = useRef<HTMLDivElement>(null);
	const [imageError, setImageError] = useState(false);

	// Compute pre-fill values exactly once on mount.
	// Priority: $draftFormData (Stage2 → Stage1 back) > localStorage (accidental leave).
	const [prefill] = useState(() =>
		draftFormData ? draftDataToFormValues(draftFormData) : (loadDraft() ?? undefined),
	);

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
	} = useListingForm("create", prefill);

	// Reset legacy create-state on Stage 1 leave (Page wrapper resets the
	// F1 draft flow on full page unmount).
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

	// Block F F1 — emit the current key params on every form change so
	// Stage 2 can detect drift against the snapshot taken at last
	// successful generation.
	useEffect(() => {
		const v = form.values;
		setCurrentParamSnapshot({
			type: v.type ?? null,
			district: v.district ?? null,
			price: v.price ?? null,
			area: v.area ?? null,
			rooms: v.rooms ?? null,
		});
	}, [
		form.values.type,
		form.values.district,
		form.values.price,
		form.values.area,
		form.values.rooms,
	]);

	const hasMinimumParams = useMemo(() => {
		const v = form.values;
		if (!v.type || !v.property_type || !v.district || !v.price || !v.area) {
			return false;
		}
		// rooms required only for residential property types
		if (
			(v.property_type === "apartment" || v.property_type === "house") &&
			!v.rooms
		) {
			return false;
		}
		return images.length > 0;
	}, [
		form.values.type,
		form.values.property_type,
		form.values.district,
		form.values.price,
		form.values.area,
		form.values.rooms,
		images.length,
	]);

	const handleError = () => {
		if (images.length === 0) {
			setImageError(true);
		}
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

		const listingData: ListingCreateData = {
			...buildListingData(values),
			images: uploadedImages.length > 0 ? uploadedImages : undefined,
		};

		try {
			await createDraftListingFx(listingData);
			webApp?.HapticFeedback.notificationOccurred("success");
			// $stage flips to 2 via the store reducer; Page.tsx routes
			// to Stage2 on next render.
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

	// Pulse animation kicks in once min params are filled — gentle hint
	// that the "next" action is available.
	const generateButtonStyle = {
		root: {
			backgroundColor: hasMinimumParams
				? "rgba(64, 167, 227, 0.85)"
				: "rgba(64, 167, 227, 0.35)",
			backdropFilter: "blur(20px) saturate(180%)",
			WebkitBackdropFilter: "blur(20px) saturate(180%)",
			boxShadow: hasMinimumParams
				? "0 4px 15px rgba(64, 167, 227, 0.4)"
				: "0 2px 8px rgba(64, 167, 227, 0.2)",
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
			<Container px="md" pt="md" pb={160}>
				<LoadingOverlay visible={isCreatingDraft} />
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
													border: "2px dashed #bae6fd",
													backgroundColor: "#f0f9ff",
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
													color="#38bdf8"
													stroke={1.5}
												/>
												<Text size="13px" fw={600} c="blue.6">
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
											{images.map((file, index) => (
												<Box
													key={index}
													style={{
														position: "relative",
														borderRadius: radii.sm,
														overflow: "hidden",
														aspectRatio: "1",
													}}
												>
													<Image
														src={URL.createObjectURL(file)}
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

						{/* Shared form fields */}
						<ListingFormFields
							form={form}
							regions={regions}
							districts={districts}
							onRegionChange={handleRegionChange}
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
								type="submit"
								style={{ flex: 1 }}
								h="100%"
								radius={100}
								c="white"
								fw={600}
								fz={14}
								disabled={!hasMinimumParams}
								loading={isCreatingDraft || isUploading}
								onClick={() => form.onSubmit(handleSubmit, handleError)()}
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
