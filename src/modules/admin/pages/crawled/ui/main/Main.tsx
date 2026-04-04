import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { formatDate, formatTimeAgo } from "@shared/lib/date";
import {
	Text,
	Group,
	Stack,
	Button,
	Image,
	Box,
	ScrollArea,
	Collapse,
	UnstyledButton,
} from "@mantine/core";
import {
	IconArrowLeft,
	IconWorldSearch,
	IconBrandTelegram,
	IconPhoto,
	IconHome,
	IconBed,
	IconRuler2,
	IconStairs,
	IconMapPin,
	IconPhone,
	IconUser,
	IconCalendar,
	IconLink,
	IconExternalLink,
	IconEye,
	IconChevronDown,
	IconChevronUp,
	IconTag,
	IconZoomIn,
	IconChevronLeft,
	IconChevronRight,
	IconX,
	IconBuildingSkyscraper,
	IconArmchair2,
	IconArrowAutofitHeight,
	IconBath,
} from "@tabler/icons-react";
import {
	fetchOLXListingById,
	fetchTelegramListingById,
} from "@shared/api/crawlerListings";
import { useTranslation } from "react-i18next";
import type { OLXListing, TelegramListing } from "@shared/api/types";
import { formatPrice } from "@app/styles/theme";
import { translateDistrict } from "@shared/lib/regions";
import "@modules/admin/shared/ui/admin.css";

/* ---------- Helpers ---------- */
function getImageUrl(img: string | { url: string }): string {
	if (typeof img === "string") return img;
	if (typeof img === "object" && img !== null && "url" in img) return img.url;
	return "";
}

function getConfidenceInfo(
	confidence: number | null,
	t: (key: string, opts?: Record<string, unknown>) => string,
) {
	if (confidence === null)
		return {
			pct: 0,
			color: "#94a3b8",
			bg: "rgba(148, 163, 184, 0.1)",
			label: t("crawledDetail.confidenceUnknown"),
		};
	const pct = Math.round(confidence * 100);
	if (pct >= 80)
		return {
			pct,
			color: "#059669",
			bg: "rgba(16, 185, 129, 0.15)",
			label: t("crawledDetail.confidenceHigh", { pct }),
		};
	if (pct >= 50)
		return {
			pct,
			color: "#d97706",
			bg: "rgba(245, 158, 11, 0.15)",
			label: t("crawledDetail.confidenceMedium", { pct }),
		};
	return {
		pct,
		color: "#dc2626",
		bg: "rgba(239, 68, 68, 0.15)",
		label: t("crawledDetail.confidenceLow", { pct }),
	};
}

function DetailRow({
	icon: Icon,
	iconBg,
	label,
	value,
}: {
	icon: typeof IconPhone;
	iconBg: string;
	label: string;
	value: React.ReactNode;
}) {
	return (
		<Box className="admin-detail-row">
			<Box className="admin-detail-icon" style={{ background: iconBg }}>
				<Icon size={18} color="white" />
			</Box>
			<Box style={{ flex: 1 }}>
				<Text size="xs" style={{ color: "#94a3b8" }}>
					{label}
				</Text>
				<Text size="sm" fw={600} style={{ color: "#1e293b" }}>
					{value}
				</Text>
			</Box>
		</Box>
	);
}

/* ---------- Image Lightbox ---------- */
function ImageLightbox({
	images,
	currentIndex,
	onClose,
	onNavigate,
}: {
	images: string[];
	currentIndex: number;
	onClose: () => void;
	onNavigate: (index: number) => void;
}) {
	useEffect(() => {
		const handler = (e: KeyboardEvent) => {
			if (e.key === "Escape") onClose();
			if (e.key === "ArrowLeft")
				onNavigate(currentIndex === 0 ? images.length - 1 : currentIndex - 1);
			if (e.key === "ArrowRight")
				onNavigate(currentIndex === images.length - 1 ? 0 : currentIndex + 1);
		};
		window.addEventListener("keydown", handler);
		return () => window.removeEventListener("keydown", handler);
	}, [currentIndex, images.length, onClose, onNavigate]);

	return (
		<Box className="admin-lightbox-overlay" onClick={onClose}>
			<Box className="admin-lightbox-close" onClick={onClose}>
				<IconX size={22} color="white" />
			</Box>
			<Box className="admin-lightbox-counter">
				{currentIndex + 1} / {images.length}
			</Box>
			<Box
				className="admin-lightbox-image-wrap"
				onClick={(e: React.MouseEvent) => e.stopPropagation()}
			>
				<Image
					src={getImageUrl(images[currentIndex])}
					fit="contain"
					style={{ maxHeight: "70vh", maxWidth: "100%" }}
				/>
			</Box>
			{images.length > 1 && (
				<>
					<Box
						className="admin-lightbox-nav admin-lightbox-nav--left"
						onClick={(e: React.MouseEvent) => {
							e.stopPropagation();
							onNavigate(
								currentIndex === 0 ? images.length - 1 : currentIndex - 1,
							);
						}}
					>
						<IconChevronLeft size={24} color="white" />
					</Box>
					<Box
						className="admin-lightbox-nav admin-lightbox-nav--right"
						onClick={(e: React.MouseEvent) => {
							e.stopPropagation();
							onNavigate(
								currentIndex === images.length - 1 ? 0 : currentIndex + 1,
							);
						}}
					>
						<IconChevronRight size={24} color="white" />
					</Box>
				</>
			)}
			{images.length > 1 && (
				<Box
					className="admin-lightbox-thumbs"
					onClick={(e: React.MouseEvent) => e.stopPropagation()}
				>
					{images.map((img, idx) => (
						<Box
							key={idx}
							className={`admin-lightbox-thumb ${idx === currentIndex ? "admin-lightbox-thumb--active" : ""}`}
							onClick={() => onNavigate(idx)}
						>
							<Image
								src={getImageUrl(img)}
								width={52}
								height={40}
								fit="cover"
								radius={8}
							/>
						</Box>
					))}
				</Box>
			)}
		</Box>
	);
}

/* ---------- Main Page ---------- */
export function Main() {
	const { source, id } = useParams<{ source: string; id: string }>();
	const navigate = useNavigate();
	const { t } = useTranslation("admin");

	const [listing, setListing] = useState<OLXListing | TelegramListing | null>(
		null,
	);
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [currentImageIndex, setCurrentImageIndex] = useState(0);
	const [lightboxOpen, setLightboxOpen] = useState(false);
	const [rawTextOpen, setRawTextOpen] = useState(false);
	const initializedRef = useRef<string | null>(null);

	const isOLX = source === "olx";

	useEffect(() => {
		if (!id || !source || initializedRef.current === `${source}-${id}`) return;
		initializedRef.current = `${source}-${id}`;

		setIsLoading(true);
		setError(null);

		const fetcher = isOLX
			? fetchOLXListingById(id)
			: fetchTelegramListingById(id);
		fetcher
			.then((data) => {
				setListing(data);
				setIsLoading(false);
			})
			.catch((err) => {
				setError(err.message || "errors.loadFailed");
				setIsLoading(false);
			});
	}, [id, source, isOLX]);

	if (isLoading || !listing) {
		return (
			<Box className="admin-page-enter" py="md" px="md">
				<Button
					variant="subtle"
					leftSection={<IconArrowLeft size={16} />}
					onClick={() => navigate("/admin/crawled")}
					className="admin-back-btn"
					color="gray"
					mb="md"
				/>
				<Stack gap={12}>
					<Box
						className="admin-skeleton"
						style={{ height: 80, borderRadius: 16 }}
					/>
					<Box
						className="admin-skeleton"
						style={{ height: 220, borderRadius: 16 }}
					/>
					<Box
						className="admin-skeleton"
						style={{ height: 160, borderRadius: 16 }}
					/>
					<Box
						className="admin-skeleton"
						style={{ height: 120, borderRadius: 16 }}
					/>
				</Stack>
			</Box>
		);
	}

	if (error) {
		return (
			<Box className="admin-page-enter" py="md" px="md">
				<Button
					variant="subtle"
					leftSection={<IconArrowLeft size={16} />}
					onClick={() => navigate("/admin/crawled")}
					className="admin-back-btn"
					color="gray"
					mb="md"
				>
					{t("common.back")}
				</Button>
				<Box className="admin-empty-state">
					<Text fw={600} style={{ color: "#dc2626" }}>
						{t(error, { defaultValue: error })}
					</Text>
				</Box>
			</Box>
		);
	}

	const olx = isOLX ? (listing as OLXListing) : null;
	const tg = !isOLX ? (listing as TelegramListing) : null;
	const conf = getConfidenceInfo(listing.confidence, t);
	const images = listing.images || [];
	const hasImages = images.length > 0;
	const allImageUrls = images.map(getImageUrl).filter(Boolean);

	return (
		<Box className="admin-page-enter" py="md" px="md">
			{/* Lightbox */}
			{lightboxOpen && hasImages && (
				<ImageLightbox
					images={allImageUrls}
					currentIndex={currentImageIndex}
					onClose={() => setLightboxOpen(false)}
					onNavigate={setCurrentImageIndex}
				/>
			)}

			{/* Back */}
			<Button
				variant="subtle"
				leftSection={<IconArrowLeft size={16} />}
				onClick={() => navigate("/admin/crawled")}
				className="admin-back-btn"
				color="gray"
				mb="md"
				size="sm"
			>
				{t("crawledDetail.backToCrawled")}
			</Button>

			{/* Source Header */}
			<Box
				className={`admin-crawled-source-header admin-crawled-source-header--${source}`}
				style={{ animationDelay: "0ms" }}
			>
				<Group justify="space-between" align="center">
					<Group gap={10}>
						<Box
							className={`admin-crawled-source-icon admin-crawled-source-icon--${source}`}
						>
							{isOLX ? (
								<IconWorldSearch size={22} color="white" />
							) : (
								<IconBrandTelegram size={22} color="white" />
							)}
						</Box>
						<Box>
							<Text fw={700} style={{ color: "#1e293b" }}>
								{isOLX ? "OLX.uz" : "Telegram"}
							</Text>
							<Text size="xs" style={{ color: "#94a3b8" }}>
								{isOLX && olx
									? t("crawledDetail.crawledAgo", {
											timeAgo: formatTimeAgo(olx.crawled_at),
										})
									: formatTimeAgo(listing.created_at)}
							</Text>
						</Box>
					</Group>
					<Box>
						{/* Confidence Badge */}
						<Box
							className="admin-confidence-detail"
							style={{ borderColor: conf.color }}
						>
							<Box className="admin-confidence-bar">
								<Box
									className="admin-confidence-bar-fill"
									style={{ width: `${conf.pct}%`, background: conf.color }}
								/>
							</Box>
							<Text size="xs" fw={700} style={{ color: conf.color }}>
								{conf.label}
							</Text>
						</Box>
					</Box>
				</Group>

				{/* External link for OLX */}
				{isOLX && olx?.url && (
					<Button
						component="a"
						href={olx.url}
						target="_blank"
						rel="noopener noreferrer"
						className="admin-external-link-btn"
						rightSection={<IconExternalLink size={14} />}
						mt={10}
						size="xs"
						radius={10}
						variant="light"
						fullWidth
					>
						{t("crawledDetail.viewOnOlx")}
					</Button>
				)}

				{/* Telegram channel */}
				{!isOLX && tg?.source_channel && (
					<Group gap={6} mt={10}>
						<IconBrandTelegram size={14} color="#0ea5e9" />
						<Text size="sm" fw={600} style={{ color: "#0ea5e9" }}>
							{tg.source_channel}
						</Text>
						{tg.message_id && (
							<Text size="xs" style={{ color: "#94a3b8" }}>
								#{tg.message_id}
							</Text>
						)}
					</Group>
				)}
			</Box>

			{/* Image Gallery */}
			{hasImages ? (
				<Box
					className="admin-gallery"
					mb="md"
					onClick={() => setLightboxOpen(true)}
					style={{ cursor: "pointer" }}
				>
					<Image
						src={getImageUrl(images[currentImageIndex])}
						height={220}
						fit="cover"
					/>
					<Box
						style={{
							position: "absolute",
							top: 10,
							left: 10,
							background: "rgba(0, 0, 0, 0.5)",
							backdropFilter: "blur(8px)",
							borderRadius: 10,
							padding: "4px 8px",
							display: "flex",
							alignItems: "center",
							gap: 4,
						}}
					>
						<IconZoomIn size={14} color="white" />
						<Text size="xs" fw={600} style={{ color: "white" }}>
							{t("common.tapToZoom")}
						</Text>
					</Box>

					{images.length > 1 && (
						<>
							<Box
								className="admin-gallery-arrow admin-gallery-arrow--left"
								onClick={(e: React.MouseEvent) => {
									e.stopPropagation();
									setCurrentImageIndex((p) =>
										p === 0 ? images.length - 1 : p - 1,
									);
								}}
							>
								<IconChevronLeft size={20} color="white" />
							</Box>
							<Box
								className="admin-gallery-arrow admin-gallery-arrow--right"
								onClick={(e: React.MouseEvent) => {
									e.stopPropagation();
									setCurrentImageIndex((p) =>
										p === images.length - 1 ? 0 : p + 1,
									);
								}}
							>
								<IconChevronRight size={20} color="white" />
							</Box>
							<Box className="admin-gallery-indicators">
								{images.map((_, idx) => (
									<Box
										key={idx}
										className={`admin-gallery-dot ${idx === currentImageIndex ? "admin-gallery-dot--active" : ""}`}
										onClick={(e: React.MouseEvent) => {
											e.stopPropagation();
											setCurrentImageIndex(idx);
										}}
										style={{ cursor: "pointer" }}
									/>
								))}
							</Box>
						</>
					)}

					<Box
						style={{
							position: "absolute",
							top: 10,
							right: 10,
							background: "rgba(0, 0, 0, 0.5)",
							backdropFilter: "blur(8px)",
							borderRadius: 20,
							padding: "3px 10px",
						}}
					>
						<Text size="xs" fw={600} style={{ color: "white" }}>
							{currentImageIndex + 1} / {images.length}
						</Text>
					</Box>

					{/* Thumbnail strip */}
					{images.length > 1 && (
						<Box
							style={{
								position: "absolute",
								bottom: 0,
								left: 0,
								right: 0,
								background: "linear-gradient(transparent, rgba(0,0,0,0.6))",
								padding: "16px 8px 8px",
								display: "flex",
								gap: 6,
								overflowX: "auto",
								scrollSnapType: "x mandatory",
							}}
						>
							{images.map((img, idx) => (
								<Box
									key={idx}
									onClick={(e: React.MouseEvent) => {
										e.stopPropagation();
										setCurrentImageIndex(idx);
									}}
									style={{
										width: 44,
										height: 32,
										borderRadius: 6,
										overflow: "hidden",
										flexShrink: 0,
										border:
											idx === currentImageIndex
												? "2px solid white"
												: "2px solid transparent",
										opacity: idx === currentImageIndex ? 1 : 0.6,
										transition: "all 0.2s ease",
										cursor: "pointer",
										scrollSnapAlign: "start",
									}}
								>
									<Image
										src={getImageUrl(img)}
										width={44}
										height={32}
										fit="cover"
									/>
								</Box>
							))}
						</Box>
					)}
				</Box>
			) : (
				<Box
					mb="md"
					style={{
						height: 100,
						background: "linear-gradient(135deg, #f1f5f9, #e2e8f0)",
						borderRadius: 16,
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
					}}
				>
					<Stack align="center" gap={4}>
						<IconPhoto size={28} color="#94a3b8" />
						<Text size="sm" c="dimmed" fw={500}>
							{t("common.noImages")}
						</Text>
					</Stack>
				</Box>
			)}

			{/* Price & Title */}
			<Box className="admin-detail-section" style={{ animationDelay: "80ms" }}>
				<Box style={{ padding: "16px" }}>
					<Text size="xl" fw={800} style={{ color: "#4f46e5" }}>
						{formatPrice(listing.price, listing.currency)}
					</Text>
					<Text size="md" fw={600} style={{ color: "#1e293b" }} mt={4}>
						{listing.description
							? listing.description.substring(0, 80)
							: `${listing.property_type} — ${listing.listing_type}`}
					</Text>
				</Box>
			</Box>

			{/* Property Quick Stats */}
			<Box
				className="admin-property-stats"
				mb="sm"
				style={{
					animation: "adminSlideUp 0.4s ease-out backwards",
					animationDelay: "120ms",
				}}
			>
				<Box className="admin-property-stat">
					<IconHome
						size={18}
						color="#6366f1"
						style={{ margin: "0 auto 4px" }}
					/>
					<Text size="xs" fw={700} style={{ color: "#1e293b" }}>
						{listing.property_type}
					</Text>
					<Text size="xs" style={{ color: "#94a3b8" }}>
						{t("common.type")}
					</Text>
				</Box>
				{listing.rooms && (
					<Box className="admin-property-stat">
						<IconBed
							size={18}
							color="#6366f1"
							style={{ margin: "0 auto 4px" }}
						/>
						<Text size="xs" fw={700} style={{ color: "#1e293b" }}>
							{listing.rooms}
						</Text>
						<Text size="xs" style={{ color: "#94a3b8" }}>
							{t("common.rooms")}
						</Text>
					</Box>
				)}
				{listing.area_sqm && (
					<Box className="admin-property-stat">
						<IconRuler2
							size={18}
							color="#6366f1"
							style={{ margin: "0 auto 4px" }}
						/>
						<Text size="xs" fw={700} style={{ color: "#1e293b" }}>
							{listing.area_sqm} m²
						</Text>
						<Text size="xs" style={{ color: "#94a3b8" }}>
							{t("common.area")}
						</Text>
					</Box>
				)}
				{listing.floor && (
					<Box className="admin-property-stat">
						<IconStairs
							size={18}
							color="#6366f1"
							style={{ margin: "0 auto 4px" }}
						/>
						<Text size="xs" fw={700} style={{ color: "#1e293b" }}>
							{listing.floor}
							{listing.total_floors ? `/${listing.total_floors}` : ""}
						</Text>
						<Text size="xs" style={{ color: "#94a3b8" }}>
							{t("common.floor")}
						</Text>
					</Box>
				)}
			</Box>

			{/* Location */}
			{(listing.district || listing.address) && (
				<Box
					className="admin-detail-section"
					style={{ animationDelay: "160ms" }}
				>
					<Box className="admin-detail-section-header">
						{t("common.location")}
					</Box>
					<Box className="admin-detail-section-body">
						{listing.district && (
							<DetailRow
								icon={IconMapPin}
								iconBg="linear-gradient(135deg, #f59e0b, #d97706)"
								label={t("common.district")}
								value={translateDistrict(listing.district, t)}
							/>
						)}
						{listing.address && (
							<DetailRow
								icon={IconMapPin}
								iconBg="linear-gradient(135deg, #6366f1, #4f46e5)"
								label={t("common.address")}
								value={listing.address}
							/>
						)}
					</Box>
				</Box>
			)}

			{/* OLX-Specific Details */}
			{isOLX && olx && (
				<Box
					className="admin-detail-section"
					style={{ animationDelay: "200ms" }}
				>
					<Box className="admin-detail-section-header">
						{t("crawledDetail.olxDetails")}
					</Box>
					<Box className="admin-detail-section-body">
						{olx.seller_name && (
							<DetailRow
								icon={IconUser}
								iconBg="linear-gradient(135deg, #6366f1, #8b5cf6)"
								label={`${t("common.seller")}${olx.seller_type ? ` (${olx.seller_type})` : ""}`}
								value={olx.seller_name}
							/>
						)}
						{olx.building_type && (
							<DetailRow
								icon={IconBuildingSkyscraper}
								iconBg="linear-gradient(135deg, #64748b, #475569)"
								label={t("crawledDetail.buildingType")}
								value={olx.building_type}
							/>
						)}
						{olx.condition && (
							<DetailRow
								icon={IconTag}
								iconBg="linear-gradient(135deg, #10b981, #059669)"
								label={t("crawledDetail.condition")}
								value={olx.condition}
							/>
						)}
						{olx.furnishing && (
							<DetailRow
								icon={IconArmchair2}
								iconBg="linear-gradient(135deg, #f59e0b, #d97706)"
								label={t("crawledDetail.furnishing")}
								value={olx.furnishing}
							/>
						)}
						{olx.ceiling_height && (
							<DetailRow
								icon={IconArrowAutofitHeight}
								iconBg="linear-gradient(135deg, #06b6d4, #0891b2)"
								label={t("crawledDetail.ceilingHeight")}
								value={`${olx.ceiling_height}m`}
							/>
						)}
						{olx.bathroom && (
							<DetailRow
								icon={IconBath}
								iconBg="linear-gradient(135deg, #8b5cf6, #7c3aed)"
								label={t("crawledDetail.bathroom")}
								value={olx.bathroom}
							/>
						)}
						{olx.views_count != null && olx.views_count > 0 && (
							<DetailRow
								icon={IconEye}
								iconBg="linear-gradient(135deg, #94a3b8, #64748b)"
								label={t("crawledDetail.viewsOnOlx")}
								value={olx.views_count.toString()}
							/>
						)}
						{olx.posted_date && (
							<DetailRow
								icon={IconCalendar}
								iconBg="linear-gradient(135deg, #64748b, #475569)"
								label={t("crawledDetail.postedOnOlx")}
								value={olx.posted_date}
							/>
						)}
					</Box>
				</Box>
			)}

			{/* Telegram-Specific Details */}
			{!isOLX && tg && (
				<Box
					className="admin-detail-section"
					style={{ animationDelay: "200ms" }}
				>
					<Box className="admin-detail-section-header">
						{t("crawledDetail.telegramDetails")}
					</Box>
					<Box className="admin-detail-section-body">
						{tg.source_channel && (
							<DetailRow
								icon={IconBrandTelegram}
								iconBg="linear-gradient(135deg, #0ea5e9, #0284c7)"
								label={t("crawledDetail.channel")}
								value={tg.source_channel}
							/>
						)}
						{tg.message_id && (
							<DetailRow
								icon={IconTag}
								iconBg="linear-gradient(135deg, #64748b, #475569)"
								label={t("crawledDetail.messageId")}
								value={`#${tg.message_id}`}
							/>
						)}
						{tg.contact_phone && (
							<DetailRow
								icon={IconPhone}
								iconBg="linear-gradient(135deg, #10b981, #059669)"
								label={t("crawledDetail.contactPhone")}
								value={tg.contact_phone}
							/>
						)}
					</Box>
				</Box>
			)}

			{/* Contact */}
			{listing.contact_phone && isOLX && (
				<Box
					className="admin-detail-section"
					style={{ animationDelay: "240ms" }}
				>
					<Box className="admin-detail-section-header">
						{t("crawledDetail.contact")}
					</Box>
					<Box className="admin-detail-section-body">
						<DetailRow
							icon={IconPhone}
							iconBg="linear-gradient(135deg, #10b981, #059669)"
							label={t("common.phone")}
							value={listing.contact_phone}
						/>
					</Box>
				</Box>
			)}

			{/* Amenities */}
			{listing.amenities && listing.amenities.length > 0 && (
				<Box
					className="admin-detail-section"
					style={{ animationDelay: "280ms" }}
				>
					<Box className="admin-detail-section-header">
						{t("crawledDetail.amenities")}
					</Box>
					<Box
						className="admin-detail-section-body"
						style={{ padding: "12px 16px" }}
					>
						<Group gap={6}>
							{listing.amenities.map((amenity, idx) => (
								<Box key={idx} className="admin-amenity-chip">
									{amenity}
								</Box>
							))}
						</Group>
					</Box>
				</Box>
			)}

			{/* Description */}
			{listing.description && (
				<Box
					className="admin-detail-section"
					style={{ animationDelay: "320ms" }}
				>
					<Box className="admin-detail-section-header">
						{t("common.description")}
					</Box>
					<Box className="admin-detail-section-body">
						<ScrollArea.Autosize mah={200}>
							<Text
								size="sm"
								style={{
									color: "#475569",
									lineHeight: 1.6,
									padding: "0 16px 12px",
								}}
							>
								{listing.description}
							</Text>
						</ScrollArea.Autosize>
					</Box>
				</Box>
			)}

			{/* Raw Text (Collapsible) */}
			{listing.raw_text && (
				<Box
					className="admin-detail-section"
					style={{ animationDelay: "360ms" }}
				>
					<UnstyledButton
						onClick={() => setRawTextOpen((o) => !o)}
						style={{ width: "100%" }}
					>
						<Group justify="space-between" style={{ padding: "10px 16px" }}>
							<Text size="sm" fw={600} style={{ color: "#64748b" }}>
								{t("crawledDetail.rawText")}
							</Text>
							{rawTextOpen ? (
								<IconChevronUp size={16} color="#94a3b8" />
							) : (
								<IconChevronDown size={16} color="#94a3b8" />
							)}
						</Group>
					</UnstyledButton>
					<Collapse in={rawTextOpen}>
						<Box style={{ padding: "0 16px 12px" }}>
							<ScrollArea.Autosize mah={300}>
								<Box className="admin-raw-text-block">
									<Text
										size="xs"
										style={{
											color: "#64748b",
											fontFamily: "monospace",
											whiteSpace: "pre-wrap",
											lineHeight: 1.6,
										}}
									>
										{listing.raw_text}
									</Text>
								</Box>
							</ScrollArea.Autosize>
						</Box>
					</Collapse>
				</Box>
			)}

			{/* Source Info */}
			<Box className="admin-detail-section" style={{ animationDelay: "400ms" }}>
				<Box className="admin-detail-section-header">
					{t("crawledDetail.metadata")}
				</Box>
				<Box className="admin-detail-section-body">
					<DetailRow
						icon={IconCalendar}
						iconBg="linear-gradient(135deg, #64748b, #475569)"
						label={t("common.created")}
						value={formatDate(listing.created_at)}
					/>
					{isOLX && olx && (
						<>
							<DetailRow
								icon={IconCalendar}
								iconBg="linear-gradient(135deg, #10b981, #059669)"
								label={t("crawledDetail.crawledAt")}
								value={formatTimeAgo(olx.crawled_at)}
							/>
							{olx.url && (
								<DetailRow
									icon={IconLink}
									iconBg="linear-gradient(135deg, #06b6d4, #0891b2)"
									label={t("crawledDetail.olxUrl")}
									value={
										<Text
											component="a"
											href={olx.url}
											target="_blank"
											size="sm"
											style={{ color: "#4f46e5", wordBreak: "break-all" }}
										>
											{olx.url}
										</Text>
									}
								/>
							)}
						</>
					)}
					{listing.signature_hash && (
						<DetailRow
							icon={IconTag}
							iconBg="linear-gradient(135deg, #94a3b8, #64748b)"
							label={t("crawledDetail.signatureHash")}
							value={
								<Text
									size="xs"
									style={{ fontFamily: "monospace", color: "#94a3b8" }}
								>
									{listing.signature_hash}
								</Text>
							}
						/>
					)}
				</Box>
			</Box>
		</Box>
	);
}
