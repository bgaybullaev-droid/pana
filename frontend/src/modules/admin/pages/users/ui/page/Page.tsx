import { useEffect, useState, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useUnit } from "effector-react";
import {
	Text,
	Group,
	Stack,
	TextInput,
	Pagination,
	UnstyledButton,
	Box,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import {
	IconSearch,
	IconChevronRight,
	IconUserSearch,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import {
	$users,
	$usersPagination,
	$isLoadingUsers,
	fetchUsers,
} from "@modules/admin/shared/state";
import "@modules/admin/shared/ui/admin.css";

const AVATAR_GRADIENTS = [
	"admin-avatar--gradient-blue",
	"admin-avatar--gradient-green",
	"admin-avatar--gradient-orange",
	"admin-avatar--gradient-red",
];

function getAvatarGradient(name: string) {
	return AVATAR_GRADIENTS[name.charCodeAt(0) % AVATAR_GRADIENTS.length];
}

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

function getRolePill(role: string) {
	const colors: Record<string, { bg: string; color: string }> = {
		admin: { bg: "rgba(239, 68, 68, 0.1)", color: "#dc2626" },
		seller: { bg: "rgba(99, 102, 241, 0.1)", color: "#4f46e5" },
		user: { bg: "rgba(148, 163, 184, 0.1)", color: "#64748b" },
	};
	const c = colors[role] || colors.user;
	return (
		<Box
			component="span"
			style={{
				background: c.bg,
				color: c.color,
				fontSize: 10,
				fontWeight: 700,
				padding: "2px 8px",
				borderRadius: 6,
				textTransform: "uppercase",
				letterSpacing: "0.3px",
			}}
		>
			{role}
		</Box>
	);
}

function formatDate(dateStr: string) {
	return new Date(dateStr).toLocaleDateString(
		localStorage.getItem("i18nextLng") === "uz" ? "uz-Latn" : "ru-RU",
		{ month: "short", day: "numeric", year: "numeric" },
	);
}

/* ---------- Chip Filter ---------- */
interface ChipOption {
	value: string | null;
	label: string;
	colorClass?: string;
}

function ChipFilter({
	options,
	value,
	onChange,
}: {
	options: ChipOption[];
	value: string | null;
	onChange: (v: string | null) => void;
}) {
	return (
		<Box className="admin-chips-scroll">
			{options.map((opt) => (
				<Box
					key={opt.value ?? "__all"}
					className={`admin-chip ${opt.colorClass || ""} ${value === opt.value ? "admin-chip--active" : ""}`}
					onClick={() => onChange(opt.value === value ? null : opt.value)}
				>
					{opt.label}
				</Box>
			))}
		</Box>
	);
}

/* ---------- Content-Aware Skeleton ---------- */
function UserCardSkeleton({ index }: { index: number }) {
	return (
		<Box className={`admin-skeleton-card admin-stagger-${index + 1}`}>
			<Group wrap="nowrap" gap={12}>
				<Box
					className="admin-skeleton-circle"
					style={{ width: 44, height: 44, flexShrink: 0 }}
				/>
				<Stack gap={6} style={{ flex: 1 }}>
					<Group gap={8}>
						<Box className="admin-skeleton-line" style={{ width: "55%" }} />
						<Box className="admin-skeleton-badge" style={{ width: 44 }} />
					</Group>
					<Box
						className="admin-skeleton-line"
						style={{ width: "40%", height: 10 }}
					/>
					<Box
						className="admin-skeleton-line"
						style={{ width: "30%", height: 9, opacity: 0.5 }}
					/>
				</Stack>
				<Box className="admin-skeleton-badge" />
			</Group>
		</Box>
	);
}

/* ---------- Main Page ---------- */
function Page() {
	const navigate = useNavigate();
	const { t } = useTranslation("admin");
	const [searchParams, setSearchParams] = useSearchParams();
	const [users, pagination, isLoading] = useUnit([
		$users,
		$usersPagination,
		$isLoadingUsers,
	]);

	const [search, setSearch] = useState(searchParams.get("q") || "");
	const [debouncedSearch] = useDebouncedValue(search, 300);
	const [approvalStatus, setApprovalStatus] = useState<string | null>(
		searchParams.get("approval_status"),
	);
	const [role, setRole] = useState<string | null>(searchParams.get("role"));
	const [page, setPage] = useState(
		parseInt(searchParams.get("page") || "1", 10),
	);
	const lastParamsRef = useRef<string | null>(null);
	const searchInputRef = useRef<HTMLInputElement>(null);

	useEffect(() => {
		const timer = setTimeout(() => {
			if (searchInputRef.current) {
				searchInputRef.current.focus();
			}
		}, 100);
		return () => clearTimeout(timer);
	}, []);

	useEffect(() => {
		const params: Record<string, string> = {};
		if (debouncedSearch) params.q = debouncedSearch;
		if (approvalStatus) params.approval_status = approvalStatus;
		if (role) params.role = role;
		if (page > 1) params.page = page.toString();

		const paramsKey = JSON.stringify({
			debouncedSearch,
			approvalStatus,
			role,
			page,
		});
		if (lastParamsRef.current === paramsKey) return;
		lastParamsRef.current = paramsKey;
		setSearchParams(params);

		fetchUsers({
			page,
			approval_status: approvalStatus || undefined,
			role: role || undefined,
			q: debouncedSearch || undefined,
		});
	}, [debouncedSearch, approvalStatus, role, page, setSearchParams]);

	const statusOptions: ChipOption[] = [
		{ value: null, label: t("common.all") },
		{
			value: "pending",
			label: t("common.pending"),
			colorClass: "admin-chip--pending",
		},
		{
			value: "approved",
			label: t("common.approved"),
			colorClass: "admin-chip--approved",
		},
		{
			value: "rejected",
			label: t("common.rejected"),
			colorClass: "admin-chip--rejected",
		},
	];

	const roleOptions: ChipOption[] = [
		{ value: null, label: t("common.allRoles") },
		{ value: "user", label: t("users.user") },
		{ value: "seller", label: t("users.seller") },
		{ value: "admin", label: t("users.admin") },
	];

	return (
		<Box className="admin-page-enter" py="md" px="md">
			{/* Page Title */}
			<Group justify="space-between" align="center" mb="md">
				<Box>
					<Text size="xl" fw={800} style={{ color: "#1e293b" }}>
						{t("users.title")}
					</Text>
					<Text size="xs" c="dimmed" fw={500}>
						{t("users.subtitle")}
					</Text>
				</Box>
				{pagination.total > 0 && (
					<Box
						style={{
							background: "rgba(99, 102, 241, 0.1)",
							borderRadius: 10,
							padding: "4px 12px",
						}}
					>
						<Text size="xs" fw={700} style={{ color: "#4f46e5" }}>
							{pagination.total}
						</Text>
					</Box>
				)}
			</Group>

			{/* Search */}
			<Box className="admin-filter-bar" style={{ marginBottom: 8 }}>
				<TextInput
					ref={searchInputRef}
					autoFocus
					placeholder={t("users.searchPlaceholder")}
					leftSection={<IconSearch size={16} color="#94a3b8" />}
					value={search}
					onChange={(e) => {
						setSearch(e.target.value);
						setPage(1);
					}}
					styles={{
						input: {
							border: "1px solid #dee2e6",
							borderRadius: 12,
							background: "#ffffff",
						},
					}}
				/>
			</Box>

			{/* Chip Filters */}
			<Stack gap={8} mb="md">
				<ChipFilter
					options={statusOptions}
					value={approvalStatus}
					onChange={(v) => {
						setApprovalStatus(v);
						setPage(1);
					}}
				/>
				<ChipFilter
					options={roleOptions}
					value={role}
					onChange={(v) => {
						setRole(v);
						setPage(1);
					}}
				/>
			</Stack>

			{/* Results */}
			{isLoading ? (
				<Stack gap={8}>
					{[0, 1, 2, 3, 4].map((i) => (
						<UserCardSkeleton key={i} index={i} />
					))}
				</Stack>
			) : users.length === 0 ? (
				<Box className="admin-empty-state">
					<Box className="admin-empty-state-icon">
						<IconUserSearch size={36} color="#94a3b8" />
					</Box>
					<Text fw={600} size="md" style={{ color: "#475569" }}>
						{t("users.noUsersFound")}
					</Text>
					<Text size="sm" c="dimmed" mt={4}>
						{t("common.tryAdjustingFilters")}
					</Text>
				</Box>
			) : (
				<Stack gap={8}>
					{users.map((user, index) => (
						<UnstyledButton
							key={user.id}
							onClick={() => navigate(`/admin/users/${user.id}`)}
							style={{ width: "100%" }}
						>
							<Box
								className={`admin-list-card admin-list-card--${user.approval_status} admin-stagger-${Math.min(index + 1, 10)}`}
							>
								<Group justify="space-between" wrap="nowrap" align="center">
									<Group wrap="nowrap" gap={12}>
										<Box
											className={`admin-avatar ${getAvatarGradient(user.first_name)}`}
											style={{
												width: 44,
												height: 44,
												display: "flex",
												alignItems: "center",
												justifyContent: "center",
												flexShrink: 0,
											}}
										>
											{user.first_name[0]?.toUpperCase()}
										</Box>
										<Stack gap={2}>
											<Group gap={6} wrap="nowrap">
												<Text
													fw={600}
													size="sm"
													lineClamp={1}
													style={{ color: "#1e293b" }}
												>
													{user.first_name} {user.last_name || ""}
												</Text>
												{getRolePill(user.role)}
											</Group>
											<Text size="xs" style={{ color: "#94a3b8" }}>
												{user.username
													? `@${user.username}`
													: user.phone || `ID: ${user.telegram_id}`}
											</Text>
											<Text size="xs" style={{ color: "#cbd5e1" }}>
												{formatDate(user.created_at)}
											</Text>
										</Stack>
									</Group>
									<Group gap={8} wrap="nowrap">
										<Box className={getBadgeClass(user.approval_status)}>
											{user.approval_status}
										</Box>
										<IconChevronRight size={16} color="#cbd5e1" />
									</Group>
								</Group>
							</Box>
						</UnstyledButton>
					))}
				</Stack>
			)}

			{/* Pagination */}
			{pagination.totalPages > 1 && (
				<Group justify="center" mt="xl">
					<Pagination
						total={pagination.totalPages}
						value={page}
						onChange={setPage}
						radius="xl"
						size="sm"
						styles={{ control: { border: "none", fontWeight: 600 } }}
					/>
				</Group>
			)}

			{users.length > 0 && (
				<Text size="xs" c="dimmed" ta="center" mt="sm" fw={500}>
					{t("users.showing", { count: users.length, total: pagination.total })}
				</Text>
			)}
		</Box>
	);
}

export const AdminUsers = {
	route: "/admin/users",
	Page,
};
