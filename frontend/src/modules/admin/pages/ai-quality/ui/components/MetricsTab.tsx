import { useEffect } from "react";
import { useUnit } from "effector-react";
import { SimpleGrid, Paper, Text, Group, Badge, Loader, Stack, Button } from "@mantine/core";

import { $metrics, fetchMetricsFx } from "../../model";

const ALERT_LABELS: Record<string, string> = {
	bad_feedback_rate: "Bad feedback rate",
	duration_p95: "Generation duration (p95)",
	daily_cost_usd: "Daily OpenAI cost",
};

export function MetricsTab() {
	const metrics = useUnit($metrics);
	const loading = useUnit(fetchMetricsFx.pending);

	useEffect(() => {
		void fetchMetricsFx();
	}, []);

	if (loading || !metrics) {
		return <Loader />;
	}

	const stats = [
		{ label: "Total generations (24h)", value: metrics.total_generations },
		{ label: "OK", value: metrics.ok_count },
		{ label: "Fallback", value: metrics.fallback_count },
		{ label: "Failures", value: metrics.failure_count },
		{
			label: "Bad-feedback rate",
			value: `${(metrics.bad_feedback_rate * 100).toFixed(1)}%`,
		},
		{
			label: "Duration p50",
			value: metrics.duration_p50_ms != null ? `${metrics.duration_p50_ms} ms` : "—",
		},
		{
			label: "Duration p95",
			value: metrics.duration_p95_ms != null ? `${metrics.duration_p95_ms} ms` : "—",
		},
		{
			label: "Spend today",
			value: `$${metrics.cost_usd_today.toFixed(2)}`,
		},
	];

	return (
		<Stack gap="md">
			<Group justify="space-between">
				<Text size="sm" c="dimmed">
					Window: last {metrics.window_hours}h
				</Text>
				<Button size="xs" variant="subtle" onClick={() => void fetchMetricsFx()}>
					Refresh
				</Button>
			</Group>
			<SimpleGrid cols={{ base: 2, md: 4 }} spacing="md">
				{stats.map((s) => (
					<Paper key={s.label} withBorder p="md" radius="md">
						<Text size="xs" c="dimmed" mb={4}>
							{s.label}
						</Text>
						<Text size="22px" fw={700}>
							{s.value}
						</Text>
					</Paper>
				))}
			</SimpleGrid>
			<Paper withBorder p="md" radius="md">
				<Text size="xs" c="dimmed" mb={8}>
					Alert states
				</Text>
				<Group gap="xs">
					{Object.entries(metrics.alert_states).map(([m, active]) => (
						<Badge
							key={m}
							color={active ? "red" : "green"}
							variant={active ? "filled" : "light"}
						>
							{ALERT_LABELS[m] ?? m}: {active ? "tripped" : "healthy"}
						</Badge>
					))}
				</Group>
			</Paper>
		</Stack>
	);
}
