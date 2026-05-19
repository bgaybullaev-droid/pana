import { useEffect, useState, useCallback } from "react";
import {
	Box,
	Button,
	Divider,
	Drawer,
	Group,
	Modal,
	NumberInput,
	Select,
	Stack,
	Switch,
	Table,
	Text,
	TextInput,
	Title,
	Loader,
	Badge,
	Tooltip,
	ActionIcon,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
	IconPlus,
	IconPencil,
	IconPlayerPause,
	IconPlayerPlay,
	IconTrash,
	IconChartBar,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { apiClient } from "@shared/api/client";
import "@modules/admin/shared/ui/admin.css";

type Source = {
	id: string;
	type: string;
	identifier: string;
	name: string;
	is_active: boolean;
	priority: "high" | "medium" | "low";
	parse_interval_minutes: number;
	total_parsed: number;
	total_errors: number;
	consecutive_errors: number;
	last_parsed_at: string | null;
	created_at: string;
	updated_at: string;
	metrics_7d: {
		listings_found: number;
		listings_extracted: number;
		listings_failed: number;
		dupes_filtered: number;
		ai_failed: number;
		notified: number;
		extraction_success_rate: number | null;
	};
};

type DailyMetric = {
	day: string;
	listings_found: number;
	listings_extracted: number;
	listings_failed: number;
	dupes_filtered: number;
	ai_failed: number;
	notified: number;
};

type MetricsRange = {
	days: number;
	totals: Source["metrics_7d"];
	daily: DailyMetric[];
};

function statusBadge(s: Source, t: (k: string) => string) {
	if (!s.is_active) {
		return (
			<Badge color="gray" variant="light">
				{t("sources.statusPaused")}
			</Badge>
		);
	}
	if (s.consecutive_errors >= 3) {
		return (
			<Badge color="red" variant="light">
				{t("sources.statusUnavailable")}
			</Badge>
		);
	}
	return (
		<Badge color="green" variant="light">
			{t("sources.statusActive")}
		</Badge>
	);
}

function fmtPercent(rate: number | null): string {
	if (rate == null) return "—";
	return `${(rate * 100).toFixed(0)}%`;
}

function Page() {
	const { t } = useTranslation("admin");
	const [sources, setSources] = useState<Source[]>([]);
	const [isLoading, setLoading] = useState(true);

	const [editing, setEditing] = useState<Source | null>(null);
	const [
		drawerOpened,
		{ open: openDrawer, close: closeDrawer },
	] = useDisclosure(false);
	const [
		confirmOpened,
		{ open: openConfirm, close: closeConfirm },
	] = useDisclosure(false);
	const [pendingDelete, setPendingDelete] = useState<Source | null>(null);

	// Metrics drawer (A8.4) — opens on row click, shows 7-day daily breakdown.
	const [
		metricsOpened,
		{ open: openMetrics, close: closeMetrics },
	] = useDisclosure(false);
	const [metricsSource, setMetricsSource] = useState<Source | null>(null);
	const [metrics, setMetrics] = useState<MetricsRange | null>(null);
	const [metricsLoading, setMetricsLoading] = useState(false);
	const [metricsDays, setMetricsDays] = useState<7 | 14 | 30>(7);

	// Drawer form state
	const [formIdentifier, setFormIdentifier] = useState("");
	const [formName, setFormName] = useState("");
	const [formType, setFormType] = useState("telegram_channel");
	const [formPriority, setFormPriority] = useState<"high" | "medium" | "low">(
		"medium",
	);
	const [formInterval, setFormInterval] = useState<number>(60);
	const [formIsActive, setFormIsActive] = useState(true);
	const [submitting, setSubmitting] = useState(false);

	const refresh = useCallback(async () => {
		setLoading(true);
		try {
			const res = await apiClient.get<Source[]>("/admin/sources");
			setSources(res.data);
		} catch (e) {
			console.error(e);
			notifications.show({
				color: "red",
				message: "Failed to load sources",
			});
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		void refresh();
	}, [refresh]);

	const startCreate = () => {
		setEditing(null);
		setFormIdentifier("");
		setFormName("");
		setFormType("telegram_channel");
		setFormPriority("medium");
		setFormInterval(60);
		setFormIsActive(true);
		openDrawer();
	};

	const startEdit = (s: Source) => {
		setEditing(s);
		setFormIdentifier(s.identifier);
		setFormName(s.name);
		setFormType(s.type);
		setFormPriority(s.priority);
		setFormInterval(s.parse_interval_minutes);
		setFormIsActive(s.is_active);
		openDrawer();
	};

	const submit = async () => {
		if (!formIdentifier.trim() || !formName.trim()) return;
		setSubmitting(true);
		try {
			if (editing) {
				await apiClient.patch(`/admin/sources/${editing.id}`, {
					name: formName.trim(),
					priority: formPriority,
					parse_interval_minutes: formInterval,
					is_active: formIsActive,
				});
			} else {
				await apiClient.post("/admin/sources", {
					type: formType,
					identifier: formIdentifier.trim(),
					name: formName.trim(),
					priority: formPriority,
					parse_interval_minutes: formInterval,
					is_active: formIsActive,
				});
			}
			closeDrawer();
			await refresh();
		} catch (e: any) {
			notifications.show({
				color: "red",
				message:
					e?.response?.data?.detail ||
					(editing ? "Update failed" : "Create failed"),
			});
		} finally {
			setSubmitting(false);
		}
	};

	const togglePause = async (s: Source) => {
		try {
			// Use the dedicated /toggle endpoint for a single-call atomic flip.
			await apiClient.post(`/admin/sources/${s.id}/toggle`);
			await refresh();
		} catch {
			notifications.show({ color: "red", message: "Toggle failed" });
		}
	};

	const loadMetrics = useCallback(
		async (source: Source, days: 7 | 14 | 30) => {
			setMetricsLoading(true);
			try {
				const res = await apiClient.get<MetricsRange>(
					`/admin/sources/${source.id}/metrics`,
					{ params: { days } },
				);
				setMetrics(res.data);
			} catch {
				notifications.show({ color: "red", message: "Failed to load metrics" });
				setMetrics(null);
			} finally {
				setMetricsLoading(false);
			}
		},
		[],
	);

	const showMetrics = (s: Source) => {
		setMetricsSource(s);
		setMetricsDays(7);
		setMetrics(null);
		openMetrics();
		void loadMetrics(s, 7);
	};

	useEffect(() => {
		if (metricsOpened && metricsSource) {
			void loadMetrics(metricsSource, metricsDays);
		}
	}, [metricsDays, metricsOpened, metricsSource, loadMetrics]);

	const askDelete = (s: Source) => {
		setPendingDelete(s);
		openConfirm();
	};

	const confirmDelete = async () => {
		if (!pendingDelete) return;
		try {
			await apiClient.delete(`/admin/sources/${pendingDelete.id}`);
			closeConfirm();
			setPendingDelete(null);
			await refresh();
		} catch {
			notifications.show({ color: "red", message: "Delete failed" });
		}
	};

	return (
		<Box p="md">
			<Group justify="space-between" mb="md">
				<Title order={3}>{t("sources.title")}</Title>
				<Button leftSection={<IconPlus size={16} />} onClick={startCreate}>
					{t("sources.add")}
				</Button>
			</Group>

			{isLoading ? (
				<Group justify="center" my="xl">
					<Loader />
				</Group>
			) : sources.length === 0 ? (
				<Text c="dimmed" ta="center" my="xl">
					{t("sources.title")}: 0
				</Text>
			) : (
				<Box style={{ overflowX: "auto" }}>
					<Table striped highlightOnHover withTableBorder>
						<Table.Thead>
							<Table.Tr>
								<Table.Th>{t("sources.username")}</Table.Th>
								<Table.Th>{t("sources.displayName")}</Table.Th>
								<Table.Th>{t("sources.kind")}</Table.Th>
								<Table.Th>{t("sources.status")}</Table.Th>
								<Table.Th>{t("sources.priority")}</Table.Th>
								<Table.Th ta="right">{t("sources.metric7dExtracted")}</Table.Th>
								<Table.Th ta="right">{t("sources.metric7dFailed")}</Table.Th>
								<Table.Th ta="right">{t("sources.metric7dDupes")}</Table.Th>
								<Table.Th ta="right">{t("sources.metric7dAiFailed")}</Table.Th>
								<Table.Th ta="right">Success%</Table.Th>
								<Table.Th ta="right" />
							</Table.Tr>
						</Table.Thead>
						<Table.Tbody>
							{sources.map((s) => (
								<Table.Tr key={s.id}>
									<Table.Td style={{ fontFamily: "monospace" }}>
										{s.identifier}
									</Table.Td>
									<Table.Td>{s.name}</Table.Td>
									<Table.Td>
										<Text size="xs" c="dimmed">
											{s.type}
										</Text>
									</Table.Td>
									<Table.Td>{statusBadge(s, t)}</Table.Td>
									<Table.Td>
										<Text size="xs" tt="capitalize">
											{s.priority}
										</Text>
									</Table.Td>
									<Table.Td ta="right">
										{s.metrics_7d.listings_extracted}
									</Table.Td>
									<Table.Td ta="right">{s.metrics_7d.listings_failed}</Table.Td>
									<Table.Td ta="right">{s.metrics_7d.dupes_filtered}</Table.Td>
									<Table.Td ta="right">{s.metrics_7d.ai_failed}</Table.Td>
									<Table.Td ta="right">
										{fmtPercent(s.metrics_7d.extraction_success_rate)}
									</Table.Td>
									<Table.Td ta="right">
										<Group gap={4} justify="flex-end" wrap="nowrap">
											<Tooltip label={t("sources.viewMetrics")}>
												<ActionIcon
													variant="subtle"
													onClick={() => showMetrics(s)}
												>
													<IconChartBar size={16} />
												</ActionIcon>
											</Tooltip>
											<Tooltip label={t("sources.actionEdit")}>
												<ActionIcon
													variant="subtle"
													onClick={() => startEdit(s)}
												>
													<IconPencil size={16} />
												</ActionIcon>
											</Tooltip>
											<Tooltip
												label={
													s.is_active
														? t("sources.actionPause")
														: t("sources.actionResume")
												}
											>
												<ActionIcon
													variant="subtle"
													color={s.is_active ? "yellow" : "green"}
													onClick={() => togglePause(s)}
												>
													{s.is_active ? (
														<IconPlayerPause size={16} />
													) : (
														<IconPlayerPlay size={16} />
													)}
												</ActionIcon>
											</Tooltip>
											<Tooltip label={t("sources.actionDelete")}>
												<ActionIcon
													variant="subtle"
													color="red"
													onClick={() => askDelete(s)}
												>
													<IconTrash size={16} />
												</ActionIcon>
											</Tooltip>
										</Group>
									</Table.Td>
								</Table.Tr>
							))}
						</Table.Tbody>
					</Table>
				</Box>
			)}

			<Drawer
				opened={drawerOpened}
				onClose={closeDrawer}
				title={editing ? t("sources.actionEdit") : t("sources.add")}
				position="right"
				size="md"
			>
				<Stack>
					<TextInput
						label={t("sources.username")}
						value={formIdentifier}
						onChange={(e) => setFormIdentifier(e.currentTarget.value)}
						disabled={!!editing}
						required
						placeholder="@channel_name"
					/>
					<TextInput
						label={t("sources.displayName")}
						value={formName}
						onChange={(e) => setFormName(e.currentTarget.value)}
						required
					/>
					<Select
						label={t("sources.kind")}
						value={formType}
						onChange={(v) => setFormType(v || "telegram_channel")}
						disabled={!!editing}
						data={[
							{ value: "telegram_channel", label: "Telegram channel" },
							{ value: "website", label: "Website" },
							{ value: "olx", label: "OLX" },
							{ value: "other", label: "Other" },
						]}
					/>
					<Select
						label={t("sources.priority")}
						value={formPriority}
						onChange={(v) =>
							setFormPriority((v || "medium") as "high" | "medium" | "low")
						}
						data={[
							{ value: "high", label: "High" },
							{ value: "medium", label: "Medium" },
							{ value: "low", label: "Low" },
						]}
					/>
					<NumberInput
						label="Parse interval (minutes)"
						min={5}
						max={1440}
						value={formInterval}
						onChange={(v) =>
							setFormInterval(typeof v === "number" ? v : Number(v) || 60)
						}
					/>
					<Switch
						label={t("sources.statusActive")}
						checked={formIsActive}
						onChange={(e) => setFormIsActive(e.currentTarget.checked)}
					/>
					<Group justify="flex-end" mt="md">
						<Button variant="default" onClick={closeDrawer}>
							{t("sources.cancelBtn")}
						</Button>
						<Button onClick={submit} loading={submitting}>
							{t("sources.saveBtn")}
						</Button>
					</Group>
				</Stack>
			</Drawer>

			<Modal
				opened={confirmOpened}
				onClose={closeConfirm}
				title={t("sources.confirmDelete")}
				centered
			>
				<Text size="sm">{pendingDelete?.identifier}</Text>
				<Group justify="flex-end" mt="md">
					<Button variant="default" onClick={closeConfirm}>
						{t("sources.cancelBtn")}
					</Button>
					<Button color="red" onClick={confirmDelete}>
						{t("sources.actionDelete")}
					</Button>
				</Group>
			</Modal>

			{/* A8.4 — per-source daily metrics drawer */}
			<Drawer
				opened={metricsOpened}
				onClose={closeMetrics}
				title={
					metricsSource
						? `${metricsSource.identifier} — ${t("sources.metricsTitle")}`
						: t("sources.metricsTitle")
				}
				position="right"
				size="lg"
			>
				<Stack>
					<Group>
						<Select
							label={t("sources.metricsRange")}
							value={String(metricsDays)}
							onChange={(v) => setMetricsDays(Number(v) as 7 | 14 | 30)}
							data={[
								{ value: "7", label: "7 d" },
								{ value: "14", label: "14 d" },
								{ value: "30", label: "30 d" },
							]}
							w={120}
						/>
					</Group>

					{metricsLoading ? (
						<Group justify="center" my="md">
							<Loader />
						</Group>
					) : metrics ? (
						<>
							<Box
								p="sm"
								style={{
									background: "#f8fafc",
									borderRadius: 8,
								}}
							>
								<Text size="xs" c="dimmed" mb={4}>
									{t("sources.metricsTotals", { days: metrics.days })}
								</Text>
								<Group gap="md" wrap="wrap">
									<Stat label={t("sources.metricParsed")} value={metrics.totals.listings_found} />
									<Stat label={t("sources.metricSaved")} value={metrics.totals.listings_extracted} />
									<Stat label={t("sources.metricFailed")} value={metrics.totals.listings_failed} />
									<Stat label={t("sources.metricDupes")} value={metrics.totals.dupes_filtered} />
									<Stat label={t("sources.metricAiFailed")} value={metrics.totals.ai_failed} />
									<Stat label={t("sources.metricNotified")} value={metrics.totals.notified} />
									<Stat
										label={t("sources.metricSuccessRate")}
										value={fmtPercent(metrics.totals.extraction_success_rate)}
									/>
								</Group>
							</Box>

							<Divider />

							<Title order={6}>{t("sources.metricsDaily")}</Title>
							{metrics.daily.length === 0 ? (
								<Text c="dimmed" size="sm">
									{t("sources.metricsEmpty")}
								</Text>
							) : (
								<Box style={{ overflowX: "auto" }}>
									<Table fontSize="xs" striped>
										<Table.Thead>
											<Table.Tr>
												<Table.Th>{t("sources.metricsDay")}</Table.Th>
												<Table.Th ta="right">{t("sources.metricParsed")}</Table.Th>
												<Table.Th ta="right">{t("sources.metricSaved")}</Table.Th>
												<Table.Th ta="right">{t("sources.metricFailed")}</Table.Th>
												<Table.Th ta="right">{t("sources.metricDupes")}</Table.Th>
												<Table.Th ta="right">{t("sources.metricNotified")}</Table.Th>
											</Table.Tr>
										</Table.Thead>
										<Table.Tbody>
											{metrics.daily.map((d) => (
												<Table.Tr key={d.day}>
													<Table.Td>{new Date(d.day).toLocaleDateString()}</Table.Td>
													<Table.Td ta="right">{d.listings_found}</Table.Td>
													<Table.Td ta="right">{d.listings_extracted}</Table.Td>
													<Table.Td ta="right">{d.listings_failed}</Table.Td>
													<Table.Td ta="right">{d.dupes_filtered}</Table.Td>
													<Table.Td ta="right">{d.notified}</Table.Td>
												</Table.Tr>
											))}
										</Table.Tbody>
									</Table>
								</Box>
							)}
						</>
					) : (
						<Text c="dimmed" size="sm">
							{t("sources.metricsEmpty")}
						</Text>
					)}
				</Stack>
			</Drawer>
		</Box>
	);
}

function Stat({ label, value }: { label: string; value: number | string }) {
	return (
		<Box>
			<Text size="xs" c="dimmed">
				{label}
			</Text>
			<Text fw={600}>{value}</Text>
		</Box>
	);
}

export const AdminSources = {
	route: "/admin/sources",
	Page,
};
