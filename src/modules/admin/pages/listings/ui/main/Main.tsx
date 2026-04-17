import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { formatPhone } from "@shared/lib/formatPhone";
import { useUnit } from "effector-react";
import { formatDate, formatDateTime } from "@shared/lib/date";
import {
	Text,
	Group,
	Stack,
	Button,
	Textarea,
	Modal,
	Image,
	Box,
	ScrollArea,
} from "@mantine/core";
import {
	IconCheck,
	IconX,
	IconArrowLeft,
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
	IconClipboardText,
	IconTag,
	IconZoomIn,
	IconChevronLeft,
	IconChevronRight,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import {
	$selectedListing,
	$isLoadingListingDetail,
	fetchListingDetail,
	approveListing,
	rejectListing,
	resetListingDetail,
	approveListingFx,
	rejectListingFx,
} from "@modules/admin/shared/state";
import { formatPrice } from "@app/styles/theme";
import { translateDistrict } from "@shared/lib/regions";
import "@modules/admin/shared/ui/admin.css";

/* ---------- Confetti Component ---------- */
function ConfettiOverlay({
	type,
	onDone,
}: {
	type: "approve" | "reject";
	onDone: () => void;
}) {
	useEffect(() => {
		const timer = setTimeout(onDone, 1200);
		return () => clearTimeout(timer);
	}, [onDone]);

	const isApprove = type === "approve";
	const colors = isApprove
		? ["#10b981", "#34d399", "#6ee7b7", "#a7f3d0", "#059669"]
		: ["#f43f5e", "#fb7185", "#fda4af", "#fecdd3", "#e11d48"];

	const particles = Array.from({ length: 12 }, (_, i) => {
		const angle = (i / 12) * 360;
		const rad = (angle * Math.PI) / 180;
		const dist = 50 + Math.random() * 30;
		return {
			cx: Math.cos(rad) * dist,
			cy: Math.sin(rad) * dist,
			color: colors[i % colors.length],
			size: 6 + Math.random() * 6,
			delay: i * 0.03,
		};
	});

	return (
		<Box className="admin-confetti-overlay">
			<Box className="admin-confetti-center">
				<Box
					className={`admin-confetti-ripple admin-confetti-ripple--${type}`}
				/>
				<Box
					className={`admin-confetti-check-circle admin-confetti-check-circle--${type}`}
				>
					<Box className="admin-confetti-check">
						<svg width={36} height={36} viewBox="0 0 24 24" fill="none">
							{isApprove ? (
								<path
									d="M5 13l4 4L19 7"
									stroke="white"
									strokeWidth={3}
									strokeLinecap="round"
									strokeLinejoin="round"
									strokeDasharray={30}
									strokeDashoffset={0}
								/>
							) : (
								<>
									<path
										d="M18 6L6 18"
										stroke="white"
										strokeWidth={3}
										strokeLinecap="round"
									/>
									<path
										d="M6 6l12 12"
										stroke="white"
										strokeWidth={3}
										strokeLinecap="round"
									/>
								</>
							)}
						</svg>
					</Box>
				</Box>
				{particles.map((p, i) => (
					<Box
						key={i}
						className="admin-confetti-particle"
						style={
							{
								"--cx": `${p.cx}px`,
								"--cy": `${p.cy}px`,
								background: p.color,
								width: p.size,
								height: p.size,
								animationDelay: `${p.delay}s`,
							} as React.CSSProperties
						}
					/>
				))}
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
	images: {
		original_url: string;
		medium_url?: string | null;
		thumbnail_url?: string | null;
	}[];
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
			{/* Close */}
			<Box className="admin-lightbox-close" onClick={onClose}>
				<IconX size={22} color="white" />
			</Box>

			{/* Counter */}
			<Box className="admin-lightbox-counter">
				{currentIndex + 1} / {images.length}
			</Box>

			{/* Main Image */}
			<Box
				className="admin-lightbox-image-wrap"
				onClick={(e: React.MouseEvent) => e.stopPropagation()}
			>
				<Image
					src={images[currentIndex]?.original_url}
					fit="contain"
					style={{ maxHeight: "70vh", maxWidth: "100%" }}
				/>
			</Box>

			{/* Navigation Arrows */}
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

			{/* Thumbnail Strip */}
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
								src={img.thumbnail_url || img.medium_url || img.original_url}
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

/* ---------- Helpers ---------- */
function getBadgeClass(status: string) {
	switch (status) {
		case "pending":
			return "admin-badge admin-badge--pending";
		case "approved":
			return "admin-badge admin-badge--approved";
		case "rejected":
			return "admin-badge admin-badge--rejected";
		default:
			return "admin-badge";
	}
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

/* ---------- Main Page ---------- */
export function Main() {
	const { id } = useParams<{ id: string }>();
	const navigate = useNavigate();
	const { t } = useTranslation("admin");
	const [listing, isLoading] = useUnit([
		$selectedListing,
		$isLoadingListingDetail,
	]);

	const [approveModalOpen, setApproveModalOpen] = useState(false);
	const [rejectModalOpen, setRejectModalOpen] = useState(false);
	const [notes, setNotes] = useState("");
	const [currentImageIndex, setCurrentImageIndex] = useState(0);
	const [lightboxOpen, setLightboxOpen] = useState(false);
	const [confetti, setConfetti] = useState<"approve" | "reject" | null>(null);
	const initializedRef = useRef<string | null>(null);
	const watchersInitializedRef = useRef(false);

	useEffect(() => {
		if (id && initializedRef.current !== id) {
			initializedRef.current = id;
			fetchListingDetail(id);
		}
		return () => {
			resetListingDetail();
		};
	}, [id]);

	useEffect(() => {
		if (watchersInitializedRef.current) return;
		watchersInitializedRef.current = true;

		const unsubApprove = approveListingFx.done.watch(() => {
			setConfetti("approve");
			setApproveModalOpen(false);
			setNotes("");
		});

		const unsubReject = rejectListingFx.done.watch(() => {
			setConfetti("reject");
			setRejectModalOpen(false);
			setNotes("");
		});

		return () => {
			unsubApprove();
			unsubReject();
		};
	}, []);

	const handleApprove = () => {
		if (id) approveListing({ listingId: id, notes: notes || undefined });
	};
	const handleReject = () => {
		if (id && notes.trim()) rejectListing({ listingId: id, notes });
	};
	const clearConfetti = useCallback(() => setConfetti(null), []);

	if (isLoading || !listing) {
		return (
			<Box className="admin-page-enter" py="md" px="md">
				<Button
					variant="subtle"
					leftSection={<IconArrowLeft size={16} />}
					onClick={() => navigate("/admin/listings")}
					className="admin-back-btn"
					color="gray"
					mb="md"
				/>
				<Stack gap={12}>
					<Box
						className="admin-skeleton"
						style={{ height: 220, borderRadius: 16 }}
					/>
					<Box
						className="admin-skeleton"
						style={{ height: 80, borderRadius: 16 }}
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

	const hasImages = listing.images.length > 0;

	return (
		<Box className="admin-page-enter" py="md" px="md">
			{confetti && <ConfettiOverlay type={confetti} onDone={clearConfetti} />}

			{/* Lightbox */}
			{lightboxOpen && hasImages && (
				<ImageLightbox
					images={listing.images}
					currentIndex={currentImageIndex}
					onClose={() => setLightboxOpen(false)}
					onNavigate={setCurrentImageIndex}
				/>
			)}

			{/* Back + Edit */}
			<Group justify="space-between" mb="md" wrap="nowrap">
				<Button
					variant="subtle"
					leftSection={<IconArrowLeft size={16} />}
					onClick={() => navigate("/admin/listings")}
					className="admin-back-btn"
					color="gray"
					size="sm"
				>
					{t("listingDetail.backToListings")}
				</Button>
				<Button
					variant="light"
					color="blue"
					size="sm"
					onClick={() => navigate(`/admin/listings/${id}/edit`)}
				>
					{t("listingDetail.edit", { defaultValue: "Edit" })}
				</Button>
			</Group>

			{/* Image Gallery */}
			{hasImages ? (
				<Box
					className="admin-gallery"
					mb="md"
					onClick={() => setLightboxOpen(true)}
					style={{ cursor: "pointer" }}
				>
					<Image
						src={
							listing.images[currentImageIndex]?.medium_url ||
							listing.images[currentImageIndex]?.original_url
						}
						height={220}
						fit="cover"
					/>

					{/* Zoom indicator */}
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

					{listing.images.length > 1 && (
						<>
							{/* Nav arrows */}
							<Box
								className="admin-gallery-arrow admin-gallery-arrow--left"
								onClick={(e: React.MouseEvent) => {
									e.stopPropagation();
									setCurrentImageIndex((prev) =>
										prev === 0 ? listing.images.length - 1 : prev - 1,
									);
								}}
							>
								<IconChevronLeft size={20} color="white" />
							</Box>
							<Box
								className="admin-gallery-arrow admin-gallery-arrow--right"
								onClick={(e: React.MouseEvent) => {
									e.stopPropagation();
									setCurrentImageIndex((prev) =>
										prev === listing.images.length - 1 ? 0 : prev + 1,
									);
								}}
							>
								<IconChevronRight size={20} color="white" />
							</Box>

							{/* Dot indicators */}
							<Box className="admin-gallery-indicators">
								{listing.images.map((_, idx) => (
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

					{/* Image counter badge */}
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
							{currentImageIndex + 1} / {listing.images.length}
						</Text>
					</Box>

					{/* Thumbnail strip below gallery */}
					{listing.images.length > 1 && (
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
							{listing.images.map((img, idx) => (
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
										src={
											img.thumbnail_url || img.medium_url || img.original_url
										}
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
						height: 140,
						background: "linear-gradient(135deg, #f1f5f9, #e2e8f0)",
						borderRadius: 16,
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
					}}
				>
					<Stack align="center" gap={8}>
						<Box
							style={{
								width: 56,
								height: 56,
								borderRadius: 16,
								background: "rgba(148, 163, 184, 0.2)",
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
							}}
						>
							<IconPhoto size={28} color="#94a3b8" />
						</Box>
						<Text size="sm" c="dimmed" fw={500}>
							{t("common.noImages")}
						</Text>
					</Stack>
				</Box>
			)}

			{/* Title & Price Header */}
			<Box className="admin-detail-section" style={{ animationDelay: "0ms" }}>
				<Box style={{ padding: "16px" }}>
					<Group justify="space-between" align="flex-start" mb={8}>
						<Box style={{ flex: 1 }}>
							<Text
								size="lg"
								fw={800}
								style={{ color: "#1e293b" }}
								lineClamp={2}
							>
								{listing.title ||
									`${listing.property_type} for ${listing.type}`}
							</Text>
							<Text size="xl" fw={800} style={{ color: "#4f46e5" }} mt={4}>
								{formatPrice(listing.price, listing.currency)}
							</Text>
						</Box>
						<Box
							className={getBadgeClass(listing.moderation_status)}
							style={{ flexShrink: 0 }}
						>
							{listing.moderation_status}
						</Box>
					</Group>
				</Box>
			</Box>

			{/* Property Quick Stats */}
			<Box
				className="admin-property-stats"
				mb="sm"
				style={{
					animation: "adminSlideUp 0.4s ease-out backwards",
					animationDelay: "80ms",
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
				{listing.area && (
					<Box className="admin-property-stat">
						<IconRuler2
							size={18}
							color="#6366f1"
							style={{ margin: "0 auto 4px" }}
						/>
						<Text size="xs" fw={700} style={{ color: "#1e293b" }}>
							{listing.area} m²
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
					style={{ animationDelay: "120ms" }}
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

			{/* Description */}
			{listing.description && (
				<Box
					className="admin-detail-section"
					style={{ animationDelay: "160ms" }}
				>
					<Box className="admin-detail-section-header">
						{t("common.description")}
					</Box>
					<Box className="admin-detail-section-body">
						<ScrollArea.Autosize mah={150}>
							<Text size="sm" style={{ color: "#475569", lineHeight: 1.6 }}>
								{listing.description}
							</Text>
						</ScrollArea.Autosize>
					</Box>
				</Box>
			)}

			{/* Seller & Contact */}
			<Box className="admin-detail-section" style={{ animationDelay: "200ms" }}>
				<Box className="admin-detail-section-header">
					{t("listingDetail.sellerContact")}
				</Box>
				<Box className="admin-detail-section-body">
					<DetailRow
						icon={IconUser}
						iconBg="linear-gradient(135deg, #6366f1, #8b5cf6)"
						label={t("common.seller")}
						value={listing.seller_name || t("common.na")}
					/>
					<DetailRow
						icon={IconPhone}
						iconBg="linear-gradient(135deg, #10b981, #059669)"
						label={t("common.phone")}
						value={
							listing.phone || listing.seller_phone
								? formatPhone(listing.phone || listing.seller_phone)
								: t("common.na")
						}
					/>
				</Box>
			</Box>

			{/* Source Info */}
			<Box className="admin-detail-section" style={{ animationDelay: "240ms" }}>
				<Box className="admin-detail-section-header">
					{t("listingDetail.sourceInfo")}
				</Box>
				<Box className="admin-detail-section-body">
					<DetailRow
						icon={IconTag}
						iconBg="linear-gradient(135deg, #8b5cf6, #7c3aed)"
						label={t("listingDetail.sourceType")}
						value={
							<Box
								component="span"
								style={{
									background:
										listing.source_type?.toUpperCase() === "MANUAL"
											? "rgba(99, 102, 241, 0.1)"
											: listing.source_type?.toUpperCase() === "CLAIMED"
												? "rgba(6, 182, 212, 0.1)"
												: "rgba(168, 85, 247, 0.1)",
									color:
										listing.source_type?.toUpperCase() === "MANUAL"
											? "#4f46e5"
											: listing.source_type?.toUpperCase() === "CLAIMED"
												? "#0891b2"
												: "#7c3aed",
									fontSize: 11,
									fontWeight: 600,
									padding: "2px 10px",
									borderRadius: 8,
									textTransform: "uppercase",
								}}
							>
								{listing.source_type}
							</Box>
						}
					/>
					<DetailRow
						icon={IconCalendar}
						iconBg="linear-gradient(135deg, #64748b, #475569)"
						label={t("common.created")}
						value={formatDate(listing.created_at)}
					/>
					{listing.source_url && (
						<DetailRow
							icon={IconLink}
							iconBg="linear-gradient(135deg, #06b6d4, #0891b2)"
							label={t("listingDetail.sourceUrl")}
							value={
								<Text
									component="a"
									href={listing.source_url}
									target="_blank"
									size="sm"
									style={{ color: "#4f46e5", wordBreak: "break-all" }}
								>
									{listing.source_url}
								</Text>
							}
						/>
					)}
				</Box>
			</Box>

			{/* Moderation Notes */}
			{(listing.moderation_notes || listing.moderated_at) && (
				<Box
					className="admin-detail-section"
					style={{ animationDelay: "280ms" }}
				>
					<Box className="admin-detail-section-header">
						{t("listingDetail.moderationHistory")}
					</Box>
					<Box className="admin-detail-section-body">
						{listing.moderation_notes && (
							<DetailRow
								icon={IconClipboardText}
								iconBg="linear-gradient(135deg, #f59e0b, #d97706)"
								label={t("common.notes")}
								value={listing.moderation_notes}
							/>
						)}
						{listing.moderated_at && (
							<DetailRow
								icon={IconCalendar}
								iconBg="linear-gradient(135deg, #64748b, #475569)"
								label={t("listingDetail.moderatedAt")}
								value={formatDateTime(listing.moderated_at)}
							/>
						)}
					</Box>
				</Box>
			)}

			{/* Action Buttons */}
			{listing.moderation_status === "pending" && (
				<Box className="admin-action-bar">
					<Group grow gap={10}>
						<Button
							className="admin-btn-reject"
							leftSection={<IconX size={18} />}
							onClick={() => setRejectModalOpen(true)}
							size="md"
							radius={14}
						>
							{t("common.reject")}
						</Button>
						<Button
							className="admin-btn-approve"
							leftSection={<IconCheck size={18} />}
							onClick={() => setApproveModalOpen(true)}
							size="md"
							radius={14}
						>
							{t("common.approve")}
						</Button>
					</Group>
				</Box>
			)}

			{/* Approve Modal — Glassmorphic Bottom Sheet */}
			<Modal
				opened={approveModalOpen}
				onClose={() => setApproveModalOpen(false)}
				title={
					<Group gap={8}>
						<Box
							style={{
								width: 32,
								height: 32,
								borderRadius: 10,
								background: "linear-gradient(135deg, #10b981, #059669)",
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
							}}
						>
							<IconCheck size={18} color="white" />
						</Box>
						<Text fw={700}>{t("listingDetail.approveListing")}</Text>
					</Group>
				}
				radius={24}
				className="admin-glass-modal"
				fullScreen={false}
				transitionProps={{ transition: "slide-up", duration: 300 }}
			>
				<Box className="admin-modal-body">
					<Box className="admin-modal-handle" />
					<Stack>
						<Text size="sm" c="dimmed">
							{t("listingDetail.approveListingDesc")}
						</Text>
						<Textarea
							label={t("common.notesOptional")}
							placeholder={t("common.addNotes")}
							value={notes}
							onChange={(e) => setNotes(e.target.value)}
							radius={12}
							autosize
							minRows={3}
						/>
						<Group justify="flex-end" mt="xs">
							<Button
								variant="subtle"
								onClick={() => setApproveModalOpen(false)}
								radius={12}
								color="gray"
							>
								{t("common.cancel")}
							</Button>
							<Button
								className="admin-btn-approve"
								onClick={handleApprove}
								loading={isLoading}
								radius={12}
							>
								{t("listingDetail.approveListing")}
							</Button>
						</Group>
					</Stack>
				</Box>
			</Modal>

			{/* Reject Modal — Glassmorphic Bottom Sheet */}
			<Modal
				opened={rejectModalOpen}
				onClose={() => setRejectModalOpen(false)}
				title={
					<Group gap={8}>
						<Box
							style={{
								width: 32,
								height: 32,
								borderRadius: 10,
								background: "linear-gradient(135deg, #f43f5e, #e11d48)",
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
							}}
						>
							<IconX size={18} color="white" />
						</Box>
						<Text fw={700}>{t("listingDetail.rejectListing")}</Text>
					</Group>
				}
				radius={24}
				className="admin-glass-modal"
				fullScreen={false}
				transitionProps={{ transition: "slide-up", duration: 300 }}
			>
				<Box className="admin-modal-body">
					<Box className="admin-modal-handle" />
					<Stack>
						<Text size="sm" c="dimmed">
							{t("listingDetail.rejectListingDesc")}
						</Text>
						<Textarea
							label={t("common.rejectionReason")}
							placeholder={t("common.enterReason")}
							value={notes}
							onChange={(e) => setNotes(e.target.value)}
							required
							radius={12}
							autosize
							minRows={3}
						/>
						<Group justify="flex-end" mt="xs">
							<Button
								variant="subtle"
								onClick={() => setRejectModalOpen(false)}
								radius={12}
								color="gray"
							>
								{t("common.cancel")}
							</Button>
							<Button
								className="admin-btn-reject"
								onClick={handleReject}
								loading={isLoading}
								disabled={!notes.trim()}
								radius={12}
							>
								{t("listingDetail.rejectListing")}
							</Button>
						</Group>
					</Stack>
				</Box>
			</Modal>
		</Box>
	);
}
