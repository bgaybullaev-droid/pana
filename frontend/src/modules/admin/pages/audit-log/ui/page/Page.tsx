/**
 * PR-I — Admin audit log page.
 *
 * Paginated, reverse-chronological feed of every audit_log row. Admin
 * filters by entity_type / action; the backend returns `actor_name`
 * pre-joined so we don't need a second round-trip per row.
 *
 * Keeps the data model simple — no export, no diff viewer — per the
 * minimum scope in docs/system-blueprint.md PR-I. Future: JSON diff
 * rendering for `old_values` / `new_values`, CSV export.
 */

import { useEffect, useState } from "react";
import {
	Box,
	Button,
	Group,
	Loader,
	Pagination,
	Select,
	Stack,
	Table,
	Text,
	Title,
} from "@mantine/core";
import { useTranslation } from "react-i18next";
import {
	fetchAuditLog,
	type AuditLogEntry,
	type AuditLogQueryParams,
} from "@shared/api/adminAudit";

const PER_PAGE = 50;

function formatDate(iso: string): string {
	try {
		return new Date(iso).toLocaleString("ru-RU");
	} catch {
		return iso;
	}
}

function compactJson(v: unknown): string {
	if (v === null || v === undefined) return "—";
	try {
		return JSON.stringify(v);
	} catch {
		return String(v);
	}
}

function Page() {
	const { t } = useTranslation("admin");
	const [entries, setEntries] = useState<AuditLogEntry[]>([]);
	const [total, setTotal] = useState(0);
	const [totalPages, setTotalPages] = useState(1);
	const [page, setPage] = useState(1);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	// Filters — committed on "Apply" so typing/changing doesn't spam the API.
	const [entityTypeDraft, setEntityTypeDraft] = useState<string>("");
	const [actionDraft, setActionDraft] = useState<string>("");
	const [committedFilters, setCommittedFilters] = useState<AuditLogQueryParams>(
		{},
	);

	const ENTITY_TYPE_OPTIONS = [
		{ value: "", label: t("auditLog.allEntities") },
		{ value: "user", label: "user" },
		{ value: "listing", label: "listing" },
		{ value: "claim", label: "claim" },
		{ value: "seller", label: "seller" },
	];

	const ACTION_OPTIONS = [
		{ value: "", label: t("auditLog.allActions") },
		{ value: "approve", label: "approve" },
		{ value: "reject", label: "reject" },
		{ value: "create", label: "create" },
		{ value: "update", label: "update" },
		{ value: "delete", label: "delete" },
	];

	useEffect(() => {
		let cancelled = false;

		async function run() {
			setLoading(true);
			setError(null);
			try {
				const params: AuditLogQueryParams = {
					page,
					per_page: PER_PAGE,
					...committedFilters,
				};
				const result = await fetchAuditLog(params);
				if (cancelled) return;
				setEntries(result.items);
				setTotal(result.total);
				setTotalPages(Math.max(1, result.total_pages));
			} catch (e: unknown) {
				if (cancelled) return;
				const msg = e instanceof Error ? e.message : String(e);
				setError(msg);
			} finally {
				if (!cancelled) setLoading(false);
			}
		}

		run();
		return () => {
			cancelled = true;
		};
	}, [page, committedFilters]);

	const handleApplyFilters = () => {
		const next: AuditLogQueryParams = {};
		if (entityTypeDraft) next.entity_type = entityTypeDraft;
		if (actionDraft) next.action = actionDraft;
		setPage(1);
		setCommittedFilters(next);
	};

	const handleResetFilters = () => {
		setEntityTypeDraft("");
		setActionDraft("");
		setPage(1);
		setCommittedFilters({});
	};

	return (
		<Box p="md">
			<Stack gap="xl">
				<Box>
					<Title order={2}>{t("auditLog.title")}</Title>
					<Text c="dimmed" size="sm" mt={4}>
						{t("auditLog.description")}
						{total > 0 ? t("auditLog.entriesCount", { count: total }) : null}
					</Text>
				</Box>

				{/* Filters */}
				<Group align="end" gap="sm" wrap="wrap">
					<Select
						label={t("auditLog.filterEntityType")}
						data={ENTITY_TYPE_OPTIONS}
						value={entityTypeDraft}
						onChange={(v) => setEntityTypeDraft(v ?? "")}
						w={180}
					/>
					<Select
						label={t("auditLog.filterAction")}
						data={ACTION_OPTIONS}
						value={actionDraft}
						onChange={(v) => setActionDraft(v ?? "")}
						w={180}
					/>
					<Button variant="filled" onClick={handleApplyFilters}>
						{t("common.apply")}
					</Button>
					<Button variant="subtle" onClick={handleResetFilters}>
						{t("common.reset")}
					</Button>
				</Group>

				{/* Error banner */}
				{error !== null && (
					<Box
						style={{
							border: "1px solid #ffa8a8",
							backgroundColor: "#fff5f5",
							borderRadius: 8,
							padding: 12,
						}}
					>
						<Text c="red" size="sm">
							{error}
						</Text>
					</Box>
				)}

				{/* Loading state */}
				{loading && (
					<Group gap="xs">
						<Loader size="xs" />
						<Text c="dimmed" size="sm">
							{t("auditLog.loading")}
						</Text>
					</Group>
				)}

				{/* Table */}
				{!loading && entries.length === 0 && !error && (
					<Text c="dimmed" size="sm">
						{t("auditLog.noEntries")}
					</Text>
				)}
				{!loading && entries.length > 0 && (
					<Table.ScrollContainer minWidth={800}>
						<Table striped highlightOnHover withTableBorder>
							<Table.Thead>
								<Table.Tr>
									<Table.Th>{t("auditLog.colWhen")}</Table.Th>
									<Table.Th>{t("auditLog.colActor")}</Table.Th>
									<Table.Th>{t("auditLog.colEntity")}</Table.Th>
									<Table.Th>{t("auditLog.colAction")}</Table.Th>
									<Table.Th>{t("auditLog.colOld")}</Table.Th>
									<Table.Th>{t("auditLog.colNew")}</Table.Th>
									<Table.Th>{t("auditLog.colIp")}</Table.Th>
								</Table.Tr>
							</Table.Thead>
							<Table.Tbody>
								{entries.map((entry) => (
									<Table.Tr key={entry.id}>
										<Table.Td style={{ whiteSpace: "nowrap" }}>
											{formatDate(entry.created_at)}
										</Table.Td>
										<Table.Td>
											{entry.actor_name ?? (
												<Text c="dimmed" size="xs">
													{t("auditLog.systemActor")}
												</Text>
											)}
										</Table.Td>
										<Table.Td>
											<Text size="xs" ff="monospace">
												{entry.entity_type}
											</Text>
											<Text size="xs" c="dimmed" ff="monospace">
												{entry.entity_id.slice(0, 8)}…
											</Text>
										</Table.Td>
										<Table.Td>
											<Text size="sm" fw={600}>
												{entry.action}
											</Text>
										</Table.Td>
										<Table.Td>
											<Text size="xs" ff="monospace" lineClamp={2}>
												{compactJson(entry.old_values)}
											</Text>
										</Table.Td>
										<Table.Td>
											<Text size="xs" ff="monospace" lineClamp={2}>
												{compactJson(entry.new_values)}
											</Text>
										</Table.Td>
										<Table.Td>
											<Text size="xs" ff="monospace" c="dimmed">
												{entry.ip_address ?? "—"}
											</Text>
										</Table.Td>
									</Table.Tr>
								))}
							</Table.Tbody>
						</Table>
					</Table.ScrollContainer>
				)}

				{/* Pagination */}
				{totalPages > 1 && (
					<Group justify="center" mt="md">
						<Pagination
							value={page}
							onChange={setPage}
							total={totalPages}
							withEdges
						/>
					</Group>
				)}
			</Stack>
		</Box>
	);
}

export const AdminAuditLog = {
	route: "/admin/audit",
	Page,
};
