/**
 * Block D (FU5) — admin read-only console for bot search telemetry.
 *
 * Surfaces the ``bot_search_queries`` capture so product can iterate the
 * parser dictionaries (top unrecognized queries) and watch the empty-result
 * share, without SSH/SQL on the VPS. No write surface — telemetry is
 * append-only and pruned by a cron.
 */

import { useEffect, useState } from "react";
import {
	Badge,
	Card,
	Container,
	Group,
	Loader,
	SegmentedControl,
	SimpleGrid,
	Stack,
	Table,
	Text,
	Title,
} from "@mantine/core";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";

import { $searchTelemetry, fetchSearchTelemetryFx } from "../../model";

function Page() {
	const data = useUnit($searchTelemetry);
	const loading = useUnit(fetchSearchTelemetryFx.pending);
	const { t } = useTranslation("admin");
	const [days, setDays] = useState("7");

	useEffect(() => {
		void fetchSearchTelemetryFx(Number(days));
	}, [days]);

	return (
		<Container size={900} py="md">
			<Group justify="space-between" align="flex-start" mb="md">
				<Stack gap={4}>
					<Title order={2}>{t("searchTelemetry.title")}</Title>
					<Text size="sm" c="dimmed" maw={560}>
						{t("searchTelemetry.subtitle")}
					</Text>
				</Stack>
				<SegmentedControl
					value={days}
					onChange={setDays}
					data={[
						{ label: t("searchTelemetry.period1"), value: "1" },
						{ label: t("searchTelemetry.period7"), value: "7" },
						{ label: t("searchTelemetry.period30"), value: "30" },
					]}
				/>
			</Group>

			{loading || !data ? (
				<Loader />
			) : (
				<Stack gap="lg">
					{/* Per-source summary */}
					<SimpleGrid cols={{ base: 1, sm: 2 }}>
						{data.by_source.length === 0 ? (
							<Text c="dimmed">{t("searchTelemetry.empty")}</Text>
						) : (
							data.by_source.map((s) => (
								<Card key={s.source} withBorder padding="md">
									<Group justify="space-between" mb="xs">
										<Text fw={600} tt="uppercase">
											{s.source}
										</Text>
										<Badge variant="light">
											{t("searchTelemetry.total")}: {s.total}
										</Badge>
									</Group>
									<Group gap="lg">
										<Stack gap={0}>
											<Text size="xl" fw={700}>
												{s.unrecognized_pct}%
											</Text>
											<Text size="xs" c="dimmed">
												{t("searchTelemetry.unrecognizedShare")} (
												{s.unrecognized})
											</Text>
										</Stack>
										<Stack gap={0}>
											<Text size="xl" fw={700}>
												{s.empty_pct}%
											</Text>
											<Text size="xs" c="dimmed">
												{t("searchTelemetry.emptyShare")} ({s.empty})
											</Text>
										</Stack>
									</Group>
								</Card>
							))
						)}
					</SimpleGrid>

					{/* Top unrecognized queries */}
					<Card withBorder padding="md">
						<Stack gap={4} mb="sm">
							<Text fw={600}>{t("searchTelemetry.topUnrecognizedTitle")}</Text>
							<Text size="xs" c="dimmed">
								{t("searchTelemetry.topUnrecognizedHint")}
							</Text>
						</Stack>
						{data.top_unrecognized.length === 0 ? (
							<Text c="dimmed" size="sm">
								{t("searchTelemetry.empty")}
							</Text>
						) : (
							<Table striped highlightOnHover>
								<Table.Thead>
									<Table.Tr>
										<Table.Th>{t("searchTelemetry.colQuery")}</Table.Th>
										<Table.Th w={90}>{t("searchTelemetry.colHits")}</Table.Th>
									</Table.Tr>
								</Table.Thead>
								<Table.Tbody>
									{data.top_unrecognized.map((r, i) => (
										<Table.Tr key={`${r.raw_text}-${i}`}>
											<Table.Td>{r.raw_text}</Table.Td>
											<Table.Td>{r.hits}</Table.Td>
										</Table.Tr>
									))}
								</Table.Tbody>
							</Table>
						)}
					</Card>

					{/* Recent queries */}
					<Card withBorder padding="md">
						<Text fw={600} mb="sm">
							{t("searchTelemetry.recentTitle")}
						</Text>
						{data.recent.length === 0 ? (
							<Text c="dimmed" size="sm">
								{t("searchTelemetry.empty")}
							</Text>
						) : (
							<Table.ScrollContainer minWidth={640}>
								<Table striped highlightOnHover>
									<Table.Thead>
										<Table.Tr>
											<Table.Th>{t("searchTelemetry.colTime")}</Table.Th>
											<Table.Th>{t("searchTelemetry.colSource")}</Table.Th>
											<Table.Th>{t("searchTelemetry.colQuery")}</Table.Th>
											<Table.Th>{t("searchTelemetry.colFields")}</Table.Th>
											<Table.Th w={80}>
												{t("searchTelemetry.colResults")}
											</Table.Th>
										</Table.Tr>
									</Table.Thead>
									<Table.Tbody>
										{data.recent.map((r, i) => (
											<Table.Tr key={`${r.created_at}-${i}`}>
												<Table.Td>
													{new Date(r.created_at).toLocaleString()}
												</Table.Td>
												<Table.Td>{r.source}</Table.Td>
												<Table.Td>{r.raw_text}</Table.Td>
												<Table.Td>
													{r.extracted_fields.length > 0 ? (
														r.extracted_fields.join(", ")
													) : (
														<Text span c="dimmed">
															—
														</Text>
													)}
												</Table.Td>
												<Table.Td>{r.results_count}</Table.Td>
											</Table.Tr>
										))}
									</Table.Tbody>
								</Table>
							</Table.ScrollContainer>
						)}
					</Card>
				</Stack>
			)}
		</Container>
	);
}

export const AdminSearchTelemetry = {
	route: "/admin/search-telemetry",
	Page,
};
