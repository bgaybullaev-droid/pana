import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useUnit } from "effector-react";
import {
	Badge,
	Box,
	Button,
	Collapse,
	Container,
	FileButton,
	Group,
	Image,
	Loader,
	LoadingOverlay,
	Modal,
	NumberInput,
	Select,
	SimpleGrid,
	Skeleton,
	Stack,
	Text,
	Textarea,
	ActionIcon,
	UnstyledButton,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
	IconCameraPlus,
	IconChevronDown,
	IconChevronUp,
	IconCircleCheck,
	IconFileText,
	IconX,
} from "@tabler/icons-react";
import { apiClient } from "@shared/api/client";
import { InnerPage } from "@shared/ui/InnerPage";
import { useTelegram } from "@app/providers/useTelegram";
import { useEffectorNotification } from "@shared/hooks/useEffectorNotification";
import { FormSection } from "@shared/ui/FormSection";
import { FeedbackLink } from "@modules/seller/feature/ai-feedback";
import { ExportButtons } from "@modules/seller/feature/text-export";
import {
	fetchListingForEdit,
	fetchListingSourceTextFx,
	fetchDraftPreviewFx,
	regenerateDraftFx,
	updateListing,
	updateListingFx,
	$editingListing,
	$isLoadingEdit,
	$isUpdating,
	$editError,
	resetEditState,
	type ListingUpdateData,
	type SourceTextData,
} from "@shared/state/listing/model";
import { useListingForm } from "@modules/seller/feature/listing-form/ui/useListingForm";
import { ListingFormFields } from "@modules/seller/feature/listing-form/ui/ListingFormFields";
import { useListingCompleteness } from "@modules/seller/feature/listing-form/ui/useListingCompleteness";
import { RequiredProgressRing } from "@modules/seller/feature/listing-form/ui/RequiredProgressRing";
import { scrollToSection } from "@modules/seller/feature/listing-form/lib/scrollToSection";
import {
	buildAiDescriptionSlots,
	type AiLang,
} from "@modules/seller/feature/listing-form/ui/aiDescriptionSlots";
import { radii, surface } from "@app/styles/theme";
import { useTelegramBackClose } from "@shared/hooks/useTelegramBackClose";

const AI_POLL_INTERVAL_MS = 2000;
const AI_POLL_MAX_ITERATIONS = 15;

function Page() {
	const navigate = useNavigate();
	const { id } = useParams<{ id: string }>();
	const { webApp } = useTelegram();
	const [editingListing, isLoading, isUpdating, editError] = useUnit([
		$editingListing,
		$isLoadingEdit,
		$isUpdating,
		$editError,
	]);
	const initializedRef = useRef<string | null>(null);
	const photoSectionRef = useRef<HTMLDivElement>(null);
	const [imageError, setImageError] = useState(false);
	const [sourceText, setSourceText] = useState<SourceTextData | null>(null);
	const [sourceTextExpanded, setSourceTextExpanded] = useState(false);

	// AI description generation state
	const [aiWishes, setAiWishes] = useState("");
	const [aiActiveTab, setAiActiveTab] = useState<AiLang>("ru");
	const [aiEdits, setAiEdits] = useState({ ru: "", uz: "", uz_cyrl: "" });
	const [aiPolling, setAiPolling] = useState(false);
	const [aiTimedOut, setAiTimedOut] = useState(false);
	const [aiRegenerating, setAiRegenerating] = useState(false);
	const aiPollIterations = useRef(0);
	const aiPollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

	// Block phase-2 — "Mark as sold" modal local state. The modal
	// itself PATCHes through apiClient (not updateListingFx) so the
	// generic edit-form's success effect chain doesn't fire here; we
	// own the success toast + redirect.
	const [sellModalOpen, setSellModalOpen] = useState(false);
	useTelegramBackClose(sellModalOpen, () => setSellModalOpen(false));
	const [soldPrice, setSoldPrice] = useState<number | "">("");
	const [soldCurrency, setSoldCurrency] = useState<"USD" | "UZS">("USD");
	const [soldNotes, setSoldNotes] = useState("");
	const [soldSubmitting, setSoldSubmitting] = useState(false);
	const [soldPriceError, setSoldPriceError] = useState<string | null>(null);

	const resetSoldModal = () => {
		setSoldPrice("");
		setSoldCurrency("USD");
		setSoldNotes("");
		setSoldPriceError(null);
	};

	const handleConfirmSold = async () => {
		if (!id) return;
		if (typeof soldPrice !== "number" || soldPrice <= 0) {
			setSoldPriceError(t("sellerSale.priceRequired"));
			return;
		}
		setSoldSubmitting(true);
		try {
			await apiClient.patch(`/listings/${id}`, {
				status: "sold",
				sold_price: soldPrice,
				sold_currency: soldCurrency,
				sold_notes: soldNotes.trim() || undefined,
			});
			notifications.show({
				title: t("notifications.success"),
				message: t("sellerSale.success"),
				color: "green",
			});
			webApp?.HapticFeedback.notificationOccurred("success");
			setSellModalOpen(false);
			resetSoldModal();
			navigate("/seller/listings");
		} catch (err: unknown) {
			const detail =
				(err as { response?: { data?: { detail?: unknown } } })?.response?.data
					?.detail;
			const message =
				typeof detail === "string"
					? detail
					: t("notifications.error");
			notifications.show({
				title: t("notifications.error"),
				message,
				color: "red",
			});
		} finally {
			setSoldSubmitting(false);
		}
	};

	const {
		form,
		images,
		isUploading,
		regions,
		districts,
		handleRegionChange,
		handleAddImages,
		handleRemoveImage,
		handleUploadImages,
		buildListingData,
		t,
	} = useListingForm("edit");

	useEffect(() => {
		if (id && initializedRef.current !== id) {
			initializedRef.current = id;
			fetchListingForEdit(id);
			// Block F F1 — fetch raw source text for master-record listings.
			// Endpoint returns {raw_text: null} for non-crawled listings;
			// we only render the expander when raw_text is non-empty.
			fetchListingSourceTextFx(id)
				.then((data) => setSourceText(data))
				.catch(() => setSourceText(null));
		}
		return () => {
			resetEditState();
			setSourceText(null);
			setSourceTextExpanded(false);
		};
	}, [id]);

	useEffect(() => {
		if (editingListing) {
			console.log("RAW_API_RESPONSE_LISTING:", editingListing);
			// S5 dual-read edit pre-fill: if a legacy listing has only the
			// old columns populated, map them to the new canonical names so
			// the form's market_type/furniture controls show the right value.
			// Backend response already mirrors both names; we pick whichever
			// is non-null.
			const mappedMarketType =
				editingListing.market_type || editingListing.building_type || undefined;
			const mappedFurniture =
				editingListing.furniture ||
				(editingListing.is_furnished === true
					? "full"
					: editingListing.is_furnished === false
						? "none"
						: undefined);
			form.setValues({
				type: editingListing.type as "sell" | "rent",
				property_type: editingListing.property_type as
					| "apartment"
					| "house"
					| "commercial"
					| "land",
				title: editingListing.title || "",
				description: editingListing.description || "",
				price: editingListing.price,
				currency: editingListing.currency as "USD" | "UZS",
				is_negotiable:
					editingListing.is_negotiable ?? editingListing.price === 0,
				rooms: editingListing.rooms ?? undefined,
				area: editingListing.area ?? undefined,
				living_area: editingListing.living_area ?? undefined,
				kitchen_area: editingListing.kitchen_area ?? undefined,
				land_area: editingListing.land_area ?? undefined,
				floor: editingListing.floor ?? undefined,
				total_floors: editingListing.total_floors ?? undefined,
				condition: editingListing.condition || undefined,
				house_type: editingListing.house_type || undefined,
				house_condition: editingListing.house_condition || [],
				location_type: editingListing.location_type || [],
				water_supply: editingListing.water_supply || [],
				electricity: editingListing.electricity || undefined,
				heating: editingListing.heating || [],
				gas_supply: editingListing.gas_supply || undefined,
				sewage: editingListing.sewage || undefined,
				land_purpose: editingListing.land_purpose || undefined,
				amenities: editingListing.amenities || [],
				nearby_amenities: editingListing.nearby_amenities || [],
				// Sprint 2 — rent group
				rent_period: editingListing.rent_period || undefined,
				deposit: editingListing.deposit ?? undefined,
				utilities_incl: editingListing.utilities_incl ?? undefined,
				min_rent_months: editingListing.min_rent_months ?? undefined,
				allowed_students: editingListing.allowed_students ?? undefined,
				allowed_pets: editingListing.allowed_pets ?? undefined,
				rent_payment: editingListing.rent_payment || [],
				// Sprint 2 — sale finance + deed
				mortgage_ok: editingListing.mortgage_ok ?? false,
				installment_ok: editingListing.installment_ok ?? false,
				halol_ok: editingListing.halol_ok ?? false,
				deed_type: editingListing.deed_type || undefined,
				// Sprint 3 — cross-cutting location (T-001)
				urgent_flag: editingListing.urgent_flag ?? false,
				microdistrict: editingListing.microdistrict || undefined,
				jk_name: editingListing.jk_name || undefined,
				landmark: editingListing.landmark || undefined,
				metro_station: editingListing.metro_station || undefined,
				seller_telegram: editingListing.seller_telegram || undefined,
				// Sprint 4 — commercial (T-009)
				commercial_type: editingListing.commercial_type || undefined,
				price_per_sqm: editingListing.price_per_sqm ?? undefined,
				ceiling_height: editingListing.ceiling_height ?? undefined,
				entrance: editingListing.entrance || undefined,
				parking_comm: editingListing.parking_comm ?? undefined,
				building_class: editingListing.building_class || undefined,
				// Sprint 5 — dual-read new columns (mapped from old on legacy rows)
				market_type: mappedMarketType,
				wall_material: editingListing.wall_material || undefined,
				furniture: mappedFurniture,
				// Sprint 6 — property polish
				garage: editingListing.garage ?? undefined,
				basement: editingListing.basement ?? undefined,
				buildings_exist: editingListing.buildings_exist ?? undefined,
				fence: editingListing.fence ?? undefined,
				land_shape: editingListing.land_shape || undefined,
				balcony: editingListing.balcony || undefined,
				listing_subtype: editingListing.listing_subtype || undefined,
				floor_plan_url: editingListing.floor_plan_url || undefined,
				// Sprint 7 — housing complex linkage
				jk_id: editingListing.jk_id || undefined,
				region: editingListing.region || "",
				district: editingListing.district || "",
				address: editingListing.address || "",
				latitude: editingListing.latitude ?? undefined,
				longitude: editingListing.longitude ?? undefined,
				phone: editingListing.phone || "",
				seller_type: editingListing.seller_type || "",
			});
		}
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [editingListing]);

	const [existingImagesList, setExistingImagesList] = useState<any[]>([]);

	useEffect(() => {
		if (editingListing?.images) {
			setExistingImagesList(editingListing.images);
		}
	}, [editingListing?.images]);

	const handleRemoveExistingImage = (imageId: string) => {
		setExistingImagesList((prev) => prev.filter((img) => img.id !== imageId));
	};

	useEffectorNotification(
		updateListingFx,
		{
			title: t("notifications.success"),
			message: t("notifications.listingUpdated"),
			color: "green",
		},
		() => {
			webApp?.HapticFeedback.notificationOccurred("success");
			navigate("/seller/listings");
		},
	);

	useEffect(() => {
		if (editError) {
			notifications.show({
				title: t("notifications.error"),
				message: editError,
				color: "red",
			});
			resetEditState();
		}
	}, [editError, t]);

	const existingImageCount = existingImagesList.length;
	const totalImageCount = existingImageCount + images.length;

	useEffect(() => {
		if (totalImageCount > 0 && imageError) {
			setImageError(false);
		}
	}, [totalImageCount, imageError]);

	const [submitAttempted, setSubmitAttempted] = useState(false);
	const { sectionStates, progress, firstIncompleteSection } =
		useListingCompleteness({
			values: form.values,
			mode: "edit",
			imageCount: totalImageCount,
			submitAttempted,
		});

	const handleError = () => {
		if (totalImageCount === 0) {
			setImageError(true);
		}
		// Paint incomplete sections red and lead the user to the first one.
		setSubmitAttempted(true);
		if (firstIncompleteSection) {
			scrollToSection(firstIncompleteSection);
		}
	};

	// AI polling loop
	useEffect(() => {
		if (!aiPolling || !id) {
			if (aiPollTimer.current) { clearTimeout(aiPollTimer.current); aiPollTimer.current = null; }
			return;
		}
		aiPollIterations.current = 0;
		const tick = async () => {
			aiPollIterations.current += 1;
			try {
				const data = await fetchDraftPreviewFx(id);
				if (data.ai_description_ru) {
					setAiEdits({
						ru: data.ai_description_ru ?? "",
						uz: data.ai_description_uz ?? "",
						uz_cyrl: data.ai_description_uz_cyrl ?? "",
					});
					setAiPolling(false);
					return;
				}
			} catch { /* network blip */ }
			if (aiPollIterations.current >= AI_POLL_MAX_ITERATIONS) {
				setAiPolling(false);
				setAiTimedOut(true);
				return;
			}
			aiPollTimer.current = setTimeout(tick, AI_POLL_INTERVAL_MS);
		};
		aiPollTimer.current = setTimeout(tick, AI_POLL_INTERVAL_MS);
		return () => { if (aiPollTimer.current) { clearTimeout(aiPollTimer.current); aiPollTimer.current = null; } };
	}, [aiPolling, id]);

	const handleAiGenerate = async () => {
		if (!id) return;
		setAiTimedOut(false);
		setAiEdits({ ru: "", uz: "", uz_cyrl: "" });
		setAiRegenerating(true);
		try {
			await regenerateDraftFx({
				id,
				triggered_by: "manual_retry",
				wishes: aiWishes.trim() || undefined,
			});
			setAiPolling(true);
			webApp?.HapticFeedback.impactOccurred("light");
		} catch {
			notifications.show({
				title: t("notifications.error"),
				message: t("createListing.regenerateFailed", "Не удалось перегенерировать. Попробуйте ещё раз."),
				color: "red",
			});
		} finally {
			setAiRegenerating(false);
		}
	};

	const handleAiRefresh = () => {
		if (!id) return;
		void fetchDraftPreviewFx(id).then((data) => {
			if (data.ai_description_ru) {
				setAiEdits({
					ru: data.ai_description_ru ?? "",
					uz: data.ai_description_uz ?? "",
					uz_cyrl: data.ai_description_uz_cyrl ?? "",
				});
				setAiTimedOut(false);
			}
		}).catch(() => undefined);
	};

	const handleSubmit = async (values: typeof form.values) => {
		if (!id) return;
		const existingCount = existingImagesList.length;
		const totalImageCount = existingCount + images.length;

		if (totalImageCount === 0) {
			setImageError(true);
			setSubmitAttempted(true);
			photoSectionRef.current?.scrollIntoView({
				behavior: "smooth",
				block: "start",
			});
			return;
		}

		const uploadedImages = await handleUploadImages(existingCount);

		// Transform kept existing images to the creation format
		const keptImages = existingImagesList.map((img, idx) => ({
			original_url: img.original_url,
			thumbnail_url: img.thumbnail_url,
			medium_url: img.medium_url,
			large_url: img.large_url,
			position: idx,
			is_primary: idx === 0,
		}));

		const finalImages = [...keptImages, ...uploadedImages]
			.slice(0, 10)
			.map((img, idx) => ({
				...img,
				position: idx,
				is_primary: idx === 0,
			}));

		const originalImageIds =
			editingListing?.images?.map((i) => i.id).join(",") || "";
		const currentImageIds = existingImagesList.map((i) => i.id).join(",");
		const isImagesModified =
			originalImageIds !== currentImageIds || uploadedImages.length > 0;

		const listingData: ListingUpdateData = {
			...buildListingData(values),
			description: aiEdits.ru.trim() || values.description || undefined,
			images: isImagesModified ? finalImages : undefined,
		};

		updateListing({ id, data: listingData });
	};

	if (isLoading) {
		return (
			<Container size={980} px="md" py="md">
				<Stack gap="md">
					<Group gap="sm">
						<Skeleton width={30} height={30} circle />
						<Skeleton width={180} height={28} />
					</Group>
					<Skeleton height={80} radius={12} />
					<Skeleton height={120} radius={12} />
					<Skeleton height={80} radius={12} />
					<Skeleton height={80} radius={12} />
					<Skeleton height={80} radius={12} />
				</Stack>
			</Container>
		);
	}

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

	// Shared AI-description block — same source on the create page. The
	// listing already exists here, so generation is always allowed (no
	// minimum-params gate) and the button spinner tracks regeneration.
	// Any language having text keeps the AI editor (tabs) open — clearing
	// all three via the field's ✕ falls back to the manual description.
	const hasAi =
		aiEdits.ru.length > 0 ||
		aiEdits.uz.length > 0 ||
		aiEdits.uz_cyrl.length > 0;
	const aiSlots = buildAiDescriptionSlots({
		t,
		hasAi,
		isPolling: aiPolling,
		pollTimedOut: aiTimedOut,
		isRegenerating: aiRegenerating,
		generateLoading: aiRegenerating,
		wishes: aiWishes,
		onWishesChange: setAiWishes,
		activeTab: aiActiveTab,
		onActiveTabChange: setAiActiveTab,
		activeText: aiEdits[aiActiveTab],
		onActiveTextChange: (val) =>
			setAiEdits((prev) => ({ ...prev, [aiActiveTab]: val })),
		onGenerate: handleAiGenerate,
		onManualRefresh: handleAiRefresh,
	});

	return (
		<InnerPage title={t("editListing.title")} noPadding>
			<Container px="md" pt="md" pb={160}>
				<LoadingOverlay visible={isUpdating || isUploading} />
				{/* Block F F5b — AI-text feedback shortcut. Renders once the
				    listing has loaded so we have a real id to attach. */}
				{id && editingListing && (
					<Box my="xs" style={{ textAlign: "right" }}>
						<FeedbackLink listingId={id} />
					</Box>
				)}

				{/* Block F F4b — Cabinet export buttons (paywall-gated). */}
				{id && editingListing && (
					<Box my="md" p="sm" style={{ border: "1px solid #e2e8f0", borderRadius: 12 }}>
						<ExportButtons listingId={id} />
					</Box>
				)}

				{/* Block phase-2 — "Mark as sold" trigger. Hidden once the
				    listing is already SOLD; the modal owns the PATCH and
				    the toast / redirect. */}
				{id && editingListing && editingListing.status !== "sold" && (
					<Box my="md">
						<Button
							fullWidth
							variant="light"
							color="green"
							leftSection={<IconCircleCheck size={18} />}
							onClick={() => {
								resetSoldModal();
								setSellModalOpen(true);
							}}
						>
							{t("sellerSale.markAsSold")}
						</Button>
					</Box>
				)}

				<Modal
					opened={sellModalOpen}
					onClose={() => {
						if (!soldSubmitting) setSellModalOpen(false);
					}}
					title={t("sellerSale.markAsSold")}
					centered
				>
					<Stack gap="sm">
						<NumberInput
							label={t("sellerSale.priceLabel")}
							value={soldPrice}
							onChange={(v) => {
								setSoldPrice(typeof v === "number" ? v : "");
								if (soldPriceError) setSoldPriceError(null);
							}}
							min={1}
							thousandSeparator=" "
							hideControls
							error={soldPriceError ?? undefined}
							required
						/>
						<Select
							label={t("sellerSale.currencyLabel")}
							value={soldCurrency}
							onChange={(v) =>
								setSoldCurrency((v as "USD" | "UZS") || "USD")
							}
							data={[
								{ value: "USD", label: "USD" },
								{ value: "UZS", label: "UZS" },
							]}
							allowDeselect={false}
						/>
						<Textarea
							placeholder={t("sellerSale.notesPlaceholder")}
							value={soldNotes}
							onChange={(e) => setSoldNotes(e.currentTarget.value)}
							autosize
							minRows={2}
							maxRows={5}
							maxLength={2000}
						/>
						<Group justify="flex-end" mt="xs">
							<Button
								variant="subtle"
								onClick={() => setSellModalOpen(false)}
								disabled={soldSubmitting}
							>
								{t("sellerSale.cancel")}
							</Button>
							<Button
								color="green"
								onClick={handleConfirmSold}
								loading={soldSubmitting}
							>
								{t("sellerSale.confirm")}
							</Button>
						</Group>
					</Stack>
				</Modal>

				{/* Block F F1 — original source text expander for master-record
				    listings. Renders only when /listings/{id}/source-text
				    returned a non-empty raw_text (crawled / aggregated rows). */}
				{sourceText?.raw_text && (
					<Box
						mb="md"
						style={{
							border: "1px solid #e2e8f0",
							borderRadius: radii.md,
							backgroundColor: "#f8fafc",
							overflow: "hidden",
						}}
					>
						<UnstyledButton
							onClick={() => setSourceTextExpanded((v) => !v)}
							style={{
								width: "100%",
								padding: "10px 14px",
								display: "flex",
								alignItems: "center",
								justifyContent: "space-between",
							}}
						>
							<Group gap={8}>
								<IconFileText size={16} color="#64748b" />
								<Text size="13px" fw={600} c="#475569">
									{t(
										"createListing.sourceText.toggle",
										"Показать исходный текст из источника",
									)}
								</Text>
								{sourceText.source && (
									<Badge
										size="xs"
										variant="light"
										color="gray"
										radius="sm"
										tt="lowercase"
									>
										{sourceText.source}
									</Badge>
								)}
							</Group>
							{sourceTextExpanded ? (
								<IconChevronUp size={16} color="#94a3b8" />
							) : (
								<IconChevronDown size={16} color="#94a3b8" />
							)}
						</UnstyledButton>
						<Collapse in={sourceTextExpanded}>
							<Box
								px="md"
								pb="md"
								style={{ borderTop: "1px solid #e2e8f0" }}
							>
								<Text
									size="12px"
									c="#475569"
									mt={10}
									style={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}
								>
									{sourceText.raw_text}
								</Text>
							</Box>
						</Collapse>
					</Box>
				)}

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
								{/* Existing images */}
								{existingImagesList.length > 0 && (
									<Box mb="sm">
										<Text size="12px" c="dimmed" mb={6} fw={500}>
											{t("editListing.currentPhotos")}
										</Text>
										<SimpleGrid cols={3} spacing="xs">
											{existingImagesList.map((image) => (
												<Box
													key={image.id}
													style={{
														position: "relative",
														aspectRatio: "1",
														borderRadius: radii.md,
														overflow: "hidden",
														border: "1px solid #f1f5f9",
													}}
												>
													<Image
														src={image.medium_url || image.original_url}
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
														onClick={() => handleRemoveExistingImage(image.id)}
													>
														<IconX size={14} />
													</ActionIcon>
												</Box>
											))}
										</SimpleGrid>
									</Box>
								)}

								{/* New images */}
								<Box>
									<Group justify="space-between" mb={6}>
										<Text size="12px" c="dimmed" fw={500}>
											{t("editListing.addNewPhotos")}
										</Text>
										<Badge size="sm" variant="light" color="blue" radius="sm">
											{totalImageCount}/10
										</Badge>
									</Group>
									<SimpleGrid cols={3} spacing="xs">
										{images.map((item, index) => (
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
												{item.kind === "pending" && (
													<Box style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", backgroundColor: "rgba(0,0,0,0.35)", zIndex: 1 }}>
														<Loader size="xs" color="white" />
													</Box>
												)}
												<Image
													src={item.kind === "uploaded" ? item.data.thumbnail_url : item.previewUrl}
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
										{totalImageCount < 10 && (
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
								{imageError && totalImageCount === 0 && (
									<Text size="13px" c="red" mt={4}>
										{t("validation.imagesRequired")}
									</Text>
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
							descriptionContentKey={aiSlots.descriptionContentKey}
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
						<style>{`
							@keyframes ctaSwap {
								from { opacity: 0; transform: translateY(2px); }
								to   { opacity: 1; transform: none; }
							}
						`}</style>
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
								loading={isUpdating || isUploading}
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
								{/* Smart CTA: shows a mini progress ring + «Ещё N полей»
								    while required fields remain, «Сохранить» when done. */}
								{isUploading ? (
									t("createListing.uploadingPhotos")
								) : progress.filled === progress.total ? (
									<span
										key="cta-ready"
										style={{ animation: "ctaSwap 200ms ease" }}
									>
										{t("editListing.save")}
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

export const EditListing = {
	route: "/seller/edit/:id",
	Page,
};
