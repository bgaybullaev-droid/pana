import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useUnit } from "effector-react";
import { formatDate, formatDateTime } from "@shared/lib/date";
import {
	Text,
	Group,
	Stack,
	Button,
	Textarea,
	Modal,
	Box,
} from "@mantine/core";
import {
	IconCheck,
	IconX,
	IconArrowLeft,
	IconPhone,
	IconBrandTelegram,
	IconLanguage,
	IconCalendar,
	IconShieldCheck,
	IconClipboardText,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import {
	$selectedUser,
	$isLoadingUserDetail,
	fetchUserDetail,
	approveUser,
	rejectUser,
	resetUserDetail,
	approveUserFx,
	rejectUserFx,
} from "@modules/admin/shared/state";
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

const AVATAR_GRADIENTS = [
	"linear-gradient(135deg, #6366f1, #8b5cf6)",
	"linear-gradient(135deg, #10b981, #059669)",
	"linear-gradient(135deg, #f59e0b, #d97706)",
	"linear-gradient(135deg, #f43f5e, #e11d48)",
];

function getAvatarGradient(name: string) {
	return AVATAR_GRADIENTS[name.charCodeAt(0) % AVATAR_GRADIENTS.length];
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
	const [user, isLoading] = useUnit([$selectedUser, $isLoadingUserDetail]);

	const [approveModalOpen, setApproveModalOpen] = useState(false);
	const [rejectModalOpen, setRejectModalOpen] = useState(false);
	const [notes, setNotes] = useState("");
	const [confetti, setConfetti] = useState<"approve" | "reject" | null>(null);
	const initializedRef = useRef<string | null>(null);
	const watchersInitializedRef = useRef(false);

	useEffect(() => {
		if (id && initializedRef.current !== id) {
			initializedRef.current = id;
			fetchUserDetail(id);
		}
		return () => {
			resetUserDetail();
		};
	}, [id]);

	useEffect(() => {
		if (watchersInitializedRef.current) return;
		watchersInitializedRef.current = true;

		const unsubApprove = approveUserFx.done.watch(() => {
			setConfetti("approve");
			setApproveModalOpen(false);
			setNotes("");
		});

		const unsubReject = rejectUserFx.done.watch(() => {
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
		if (id) approveUser({ userId: id, notes: notes || undefined });
	};
	const handleReject = () => {
		if (id && notes.trim()) rejectUser({ userId: id, notes });
	};
	const clearConfetti = useCallback(() => setConfetti(null), []);

	if (isLoading || !user) {
		return (
			<Box className="admin-page-enter" py="md" px="md">
				<Button
					variant="subtle"
					leftSection={<IconArrowLeft size={16} />}
					onClick={() => navigate("/admin/users")}
					className="admin-back-btn"
					color="gray"
					mb="md"
				/>
				<Stack gap={12}>
					<Box
						className="admin-skeleton"
						style={{ height: 120, borderRadius: 16 }}
					/>
					<Box
						className="admin-skeleton"
						style={{ height: 200, borderRadius: 16 }}
					/>
					<Box
						className="admin-skeleton"
						style={{ height: 140, borderRadius: 16 }}
					/>
				</Stack>
			</Box>
		);
	}

	return (
		<Box className="admin-page-enter" py="md" px="md">
			{confetti && <ConfettiOverlay type={confetti} onDone={clearConfetti} />}

			<Button
				variant="subtle"
				leftSection={<IconArrowLeft size={16} />}
				onClick={() => navigate("/admin/users")}
				className="admin-back-btn"
				color="gray"
				mb="md"
				size="sm"
			>
				{t("userDetail.backToUsers")}
			</Button>

			{/* Profile Header */}
			<Box className="admin-detail-section" style={{ animationDelay: "0ms" }}>
				<Box style={{ padding: "20px 16px", textAlign: "center" }}>
					<Box
						style={{
							width: 72,
							height: 72,
							borderRadius: 20,
							background: getAvatarGradient(user.first_name),
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							margin: "0 auto 12px",
							color: "white",
							fontSize: 28,
							fontWeight: 800,
							boxShadow: "0 8px 24px rgba(99, 102, 241, 0.25)",
						}}
					>
						{user.first_name[0]?.toUpperCase()}
					</Box>
					<Text size="lg" fw={800} style={{ color: "#1e293b" }}>
						{user.first_name} {user.last_name || ""}
					</Text>
					{user.username && (
						<Text size="sm" style={{ color: "#94a3b8" }}>
							@{user.username}
						</Text>
					)}
					<Group justify="center" gap={8} mt={10}>
						<Box className={getBadgeClass(user.approval_status)}>
							{user.approval_status}
						</Box>
						<Box
							component="span"
							style={{
								background:
									user.role === "admin"
										? "rgba(239, 68, 68, 0.1)"
										: user.role === "seller"
											? "rgba(99, 102, 241, 0.1)"
											: "rgba(148, 163, 184, 0.1)",
								color:
									user.role === "admin"
										? "#dc2626"
										: user.role === "seller"
											? "#4f46e5"
											: "#64748b",
								fontSize: 10,
								fontWeight: 700,
								padding: "4px 10px",
								borderRadius: 20,
								textTransform: "uppercase",
								letterSpacing: "0.3px",
							}}
						>
							{user.role}
						</Box>
					</Group>
				</Box>
			</Box>

			{/* Contact */}
			<Box className="admin-detail-section" style={{ animationDelay: "80ms" }}>
				<Box className="admin-detail-section-header">
					{t("userDetail.contactInfo")}
				</Box>
				<Box className="admin-detail-section-body">
					<DetailRow
						icon={IconPhone}
						iconBg="linear-gradient(135deg, #10b981, #059669)"
						label={t("common.phone")}
						value={user.phone || t("common.notProvided")}
					/>
					<DetailRow
						icon={IconBrandTelegram}
						iconBg="linear-gradient(135deg, #06b6d4, #0891b2)"
						label={t("userDetail.telegramId")}
						value={user.telegram_id}
					/>
					<DetailRow
						icon={IconLanguage}
						iconBg="linear-gradient(135deg, #8b5cf6, #7c3aed)"
						label={t("userDetail.language")}
						value={
							user.language === "ru"
								? t("userDetail.russian")
								: user.language === "uz"
									? t("userDetail.uzbek")
									: user.language
						}
					/>
				</Box>
			</Box>

			{/* Account Status */}
			<Box className="admin-detail-section" style={{ animationDelay: "160ms" }}>
				<Box className="admin-detail-section-header">
					{t("userDetail.accountStatus")}
				</Box>
				<Box className="admin-detail-section-body">
					<DetailRow
						icon={IconCalendar}
						iconBg="linear-gradient(135deg, #6366f1, #4f46e5)"
						label={t("userDetail.registered")}
						value={formatDate(user.created_at)}
					/>
					<DetailRow
						icon={IconShieldCheck}
						iconBg={
							user.onboarding_completed
								? "linear-gradient(135deg, #10b981, #059669)"
								: "linear-gradient(135deg, #94a3b8, #64748b)"
						}
						label={t("userDetail.onboarding")}
						value={
							<Box
								component="span"
								style={{
									background: user.onboarding_completed
										? "rgba(16, 185, 129, 0.1)"
										: "rgba(148, 163, 184, 0.1)",
									color: user.onboarding_completed ? "#059669" : "#64748b",
									fontSize: 11,
									fontWeight: 600,
									padding: "2px 10px",
									borderRadius: 8,
								}}
							>
								{user.onboarding_completed
									? t("userDetail.completed")
									: t("userDetail.notCompleted")}
							</Box>
						}
					/>
				</Box>
			</Box>

			{/* Review History */}
			{(user.approval_notes || user.approved_at) && (
				<Box
					className="admin-detail-section"
					style={{ animationDelay: "240ms" }}
				>
					<Box className="admin-detail-section-header">
						{t("userDetail.reviewHistory")}
					</Box>
					<Box className="admin-detail-section-body">
						{user.approval_notes && (
							<DetailRow
								icon={IconClipboardText}
								iconBg="linear-gradient(135deg, #f59e0b, #d97706)"
								label={t("common.notes")}
								value={user.approval_notes}
							/>
						)}
						{user.approved_at && (
							<DetailRow
								icon={IconCalendar}
								iconBg="linear-gradient(135deg, #64748b, #475569)"
								label={t("userDetail.reviewedAt")}
								value={formatDateTime(user.approved_at)}
							/>
						)}
					</Box>
				</Box>
			)}

			{/* Actions */}
			{user.approval_status === "pending" && (
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
						<Text fw={700}>{t("userDetail.approveUser")}</Text>
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
							{t("userDetail.approveUserDesc")}
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
								{t("userDetail.approveUser")}
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
						<Text fw={700}>{t("userDetail.rejectUser")}</Text>
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
							{t("userDetail.rejectUserDesc")}
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
								{t("userDetail.rejectUser")}
							</Button>
						</Group>
					</Stack>
				</Box>
			</Modal>
		</Box>
	);
}
