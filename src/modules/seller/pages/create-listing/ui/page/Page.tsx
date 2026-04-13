import { useEffect, useRef, useState } from "react";
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
import { useEffectorNotification } from "@shared/hooks/useEffectorNotification";
import { FormSection } from "@shared/ui/FormSection";
import {
	createListing,
	createListingFx,
	$isCreating,
	$createError,
	resetCreateState,
	type ListingCreateData,
} from "@shared/state/listing/model";
import { useListingForm } from "@modules/seller/feature/listing-form/ui/useListingForm";
import { ListingFormFields } from "@modules/seller/feature/listing-form/ui/ListingFormFields";
import { radii, shadows, surface } from "@app/styles/theme";

function Page() {
	const navigate = useNavigate();
	const { webApp } = useTelegram();
	const [isCreating, createError] = useUnit([$isCreating, $createError]);
	const photoSectionRef = useRef<HTMLDivElement>(null);
	const [imageError, setImageError] = useState(false);

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
	} = useListingForm();

	useEffect(() => {
		return () => {
			resetCreateState();
		};
	}, []);

	useEffectorNotification(
		createListingFx,
		{
			title: t("notifications.success"),
			message: t("notifications.listingCreated"),
			color: "green",
		},
		() => {
			webApp?.HapticFeedback.notificationOccurred("success");
			navigate("/seller/listings");
		},
	);

	useEffect(() => {
		if (createError) {
			notifications.show({
				title: t("notifications.error"),
				message: createError,
				color: "red",
			});
			resetCreateState();
		}
	}, [createError, t]);

	useEffect(() => {
		if (images.length > 0 && imageError) {
			setImageError(false);
		}
	}, [images.length, imageError]);

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

		createListing(listingData);
	};

		const errorCount = Object.keys(form.errors).length + (images.length === 0 && imageError ? 1 : 0);

		return (
			<InnerPage title={t("createListing.title")} noPadding>
				<Container px="md" pt="md" pb={160}>
					<LoadingOverlay visible={isCreating} />
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
														aspectRatio: "1",
														borderRadius: radii.md,
														overflow: "hidden",
														border: "1px solid #f1f5f9",
													}}
												>
													<Image
														src={URL.createObjectURL(file)}
														alt=""
														fit="cover"
														h="100%"
													/>
													<ActionIcon
														variant="filled"
														color="red"
														size="sm"
														radius="xl"
														style={{ position: "absolute", top: 4, right: 4 }}
														onClick={() => handleRemoveImage(index)}
													>
														<IconX size={14} />
													</ActionIcon>
												</Box>
											))}
											{images.length < 10 && (
												<FileButton
													onChange={handleAddImages}
													accept="image/*"
													multiple
												>
													{(props) => (
														<Box
															{...props}
															style={{
																aspectRatio: "1",
																borderRadius: radii.md,
																border: "2px dashed #cbd5e1",
																backgroundColor: surface.page,
																display: "flex",
																alignItems: "center",
																justifyContent: "center",
																cursor: "pointer",
															}}
														>
															<IconCameraPlus
																size={22}
																color="#94a3b8"
																stroke={1.5}
															/>
														</Box>
													)}
												</FileButton>
											)}
										</SimpleGrid>
									</Box>
								)}
								{imageError && images.length === 0 && (
									<Text size="13px" c="red" mt={4}>
										{t("validation.imagesRequired") ||
											"Добавьте хотя бы одно фото"}
									</Text>
								)}
							</FormSection>
						</div>

						{/* Shared form fields: Type, Main Info, Parameters, Location, Price, Contact */}
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
										defaultValue: `Осталось заполнить ${errorCount} полей. Прокрутите вверх.`,
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
								loading={isCreating || isUploading}
								onClick={() => form.onSubmit(handleSubmit, handleError)()}
								styles={{
									root: { 
										backgroundColor: "rgba(64, 167, 227, 0.55)",
										backdropFilter: "blur(20px) saturate(180%)",
										WebkitBackdropFilter: "blur(20px) saturate(180%)",
										boxShadow: "0 4px 15px rgba(64, 167, 227, 0.4)",
										border: "1px solid rgba(255, 255, 255, 0.2)",
									},
								}}
							>
								{isUploading
									? t("createListing.uploadingPhotos")
									: t("createListing.publish")}
							</Button>
						</Box>
					</Box>
				</Box>
			</Container>
		</InnerPage>
	);
}

export const CreateListing = {
	route: "/seller/create",
	Page,
};
