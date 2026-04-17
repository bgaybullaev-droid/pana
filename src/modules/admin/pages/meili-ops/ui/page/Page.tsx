/**
 * PR-D — Admin Meilisearch ops panel.
 *
 * Shows live counters from the in-process `_BACKFILL_COUNTERS` dict and
 * exposes a one-click full-table reindex button. Counters refresh every
 * 10s while the page is mounted.
 *
 * The reindex endpoint is synchronous on the backend side (streams
 * through batches) so the button shows a loading state until the
 * response lands. Result counts are surfaced in a success notification.
 */

import { useEffect, useRef, useState } from "react";
import {
	Box,
	Button,
	Group,
	Loader,
	SimpleGrid,
	Stack,
	Table,
	Text,
	Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
	getMeiliCounters,
	reindexAllMeili,
	type MeiliCounters,
	type MeiliReindexResult,
} from "@shared/api/adminOps";

const COUNTER_ROWS: Array<{
	key: keyof MeiliCounters;
	label: string;
	kind: "success" | "failure";
}> = [
	{
		key: "meili_backfill_success_total",
		label: "Backfill success",
		kind: "success",
	},
	{
		key: "meili_backfill_failure_total",
		label: "Backfill failure",
		kind: "failure",
	},
	{
		key: "meili_index_success_total",
		label: "Per-write index success",
		kind: "success",
	},
	{
		key: "meili_index_failure_total",
		label: "Per-write index failure",
		kind: "failure",
	},
	{
		key: "meili_delete_success_total",
		label: "Delete success",
		kind: "success",
	},
	{
		key: "meili_delete_failure_total",
		label: "Delete failure",
		kind: "failure",
	},
];

const POLL_INTERVAL_MS = 10_000;

function Page() {
	const [counters, setCounters] = useState<MeiliCounters | null>(null);
	const [countersError, setCountersError] = useState<string | null>(null);
	const [isReindexing, setIsReindexing] = useState(false);
	const [lastResult, setLastResult] = useState<MeiliReindexResult | null>(null);
	const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

	// Poll counters. `refresh` is a stable closure that reschedules itself;
	// we clear the timer on unmount so stopping the page closes the loop.
	useEffect(() => {
		let cancelled = false;

		async function refresh() {
			try {
				const data = await getMeiliCounters();
				if (cancelled) return;
				setCounters(data);
				setCountersError(null);
			} catch (e: unknown) {
				if (cancelled) return;
				const msg = e instanceof Error ? e.message : String(e);
				setCountersError(msg);
			} finally {
				if (!cancelled) {
					pollTimerRef.current = setTimeout(refresh, POLL_INTERVAL_MS);
				}
			}
		}

		refresh();

		return () => {
			cancelled = true;
			if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
		};
	}, []);

	const handleReindex = async () => {
		if (isReindexing) return;
		setIsReindexing(true);
		try {
			const result = await reindexAllMeili();
			setLastResult(result);
			notifications.show({
				title: "Reindex complete",
				message: `Indexed ${result.indexed_count} / failed ${result.failed_count}`,
				color: result.failed_count > 0 ? "yellow" : "green",
			});
			// Refresh counters immediately so the new totals show up.
			try {
				const fresh = await getMeiliCounters();
				setCounters(fresh);
			} catch {
				// Counter refresh is best-effort — poll loop will catch up.
			}
		} catch (e: unknown) {
			const msg = e instanceof Error ? e.message : String(e);
			notifications.show({
				title: "Reindex failed",
				message: msg,
				color: "red",
			});
		} finally {
			setIsReindexing(false);
		}
	};

	return (
		<Box p="md">
			<Stack gap="xl">
				<Box>
					<Title order={2}>Meilisearch ops</Title>
					<Text c="dimmed" size="sm" mt={4}>
						Live counters from the backend's in-process metrics + one-click
						full-table reindex.
					</Text>
				</Box>

				{/* Counters card */}
				<Box
					style={{
						border: "1px solid #e9ecef",
						borderRadius: 12,
						padding: 16,
					}}
				>
					<Group justify="space-between" mb="sm">
						<Text fw={600}>Counters</Text>
						<Text size="xs" c="dimmed">
							Auto-refresh every {POLL_INTERVAL_MS / 1000}s
						</Text>
					</Group>
					{counters === null && countersError === null && (
						<Group gap="xs">
							<Loader size="xs" />
							<Text size="sm" c="dimmed">
								Loading counters…
							</Text>
						</Group>
					)}
					{countersError !== null && counters === null && (
						<Text size="sm" c="red">
							{countersError}
						</Text>
					)}
					{counters !== null && (
						<Table highlightOnHover withRowBorders={false}>
							<Table.Tbody>
								{COUNTER_ROWS.map((row) => (
									<Table.Tr key={row.key}>
										<Table.Td>{row.label}</Table.Td>
										<Table.Td
											style={{
												textAlign: "right",
												fontVariantNumeric: "tabular-nums",
												color:
													row.kind === "failure" && counters[row.key] > 0
														? "#c92a2a"
														: "#212529",
												fontWeight: 600,
											}}
										>
											{counters[row.key].toLocaleString("ru-RU")}
										</Table.Td>
									</Table.Tr>
								))}
							</Table.Tbody>
						</Table>
					)}
				</Box>

				{/* Reindex card */}
				<Box
					style={{
						border: "1px solid #e9ecef",
						borderRadius: 12,
						padding: 16,
					}}
				>
					<Text fw={600} mb="xs">
						Full-table reindex
					</Text>
					<Text size="sm" c="dimmed" mb="md">
						Streams every ACTIVE, non-deleted listing through the indexer. Safe
						to re-run — Meili upserts by primary key.
					</Text>
					{lastResult && (
						<SimpleGrid cols={2} mb="md">
							<Box>
								<Text size="xs" c="dimmed">
									Last run — indexed
								</Text>
								<Text fw={600} size="lg">
									{lastResult.indexed_count.toLocaleString("ru-RU")}
								</Text>
							</Box>
							<Box>
								<Text size="xs" c="dimmed">
									Last run — failed
								</Text>
								<Text
									fw={600}
									size="lg"
									c={lastResult.failed_count > 0 ? "red" : "dimmed"}
								>
									{lastResult.failed_count.toLocaleString("ru-RU")}
								</Text>
							</Box>
						</SimpleGrid>
					)}
					<Button color="blue" loading={isReindexing} onClick={handleReindex}>
						{isReindexing ? "Reindexing…" : "Reindex all listings"}
					</Button>
				</Box>
			</Stack>
		</Box>
	);
}

export const AdminMeiliOps = {
	route: "/admin/ops/meili",
	Page,
};
