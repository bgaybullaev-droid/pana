/**
 * Block F V2.0 (F5b) — admin AI-quality dashboard.
 *
 * Tabs: Metrics / Generations / Feedback / Prompts. Each tab is a
 * standalone component reading from its own effector effect; tab
 * switches don't tear down siblings, just hide them so navigating
 * between tabs is instant once data has been fetched once.
 */

import { Container, Stack, Tabs, Text, Title } from "@mantine/core";
import {
	IconChartBar,
	IconList,
	IconMessage,
	IconBraces,
} from "@tabler/icons-react";

import { MetricsTab } from "../components/MetricsTab";
import { GenerationsTab } from "../components/GenerationsTab";
import { FeedbackTab } from "../components/FeedbackTab";
import { PromptsTab } from "../components/PromptsTab";

function Page() {
	return (
		<Container size={1200} py="md">
			<Stack gap="sm" mb="md">
				<Title order={2}>AI Quality</Title>
				<Text size="sm" c="dimmed">
					Block F V2.0 — generation telemetry, seller feedback, prompt versions.
				</Text>
			</Stack>
			<Tabs defaultValue="metrics" keepMounted>
				<Tabs.List>
					<Tabs.Tab value="metrics" leftSection={<IconChartBar size={14} />}>
						Metrics
					</Tabs.Tab>
					<Tabs.Tab value="generations" leftSection={<IconList size={14} />}>
						Generations
					</Tabs.Tab>
					<Tabs.Tab value="feedback" leftSection={<IconMessage size={14} />}>
						Feedback
					</Tabs.Tab>
					<Tabs.Tab value="prompts" leftSection={<IconBraces size={14} />}>
						Prompts
					</Tabs.Tab>
				</Tabs.List>
				<Tabs.Panel value="metrics" pt="md">
					<MetricsTab />
				</Tabs.Panel>
				<Tabs.Panel value="generations" pt="md">
					<GenerationsTab />
				</Tabs.Panel>
				<Tabs.Panel value="feedback" pt="md">
					<FeedbackTab />
				</Tabs.Panel>
				<Tabs.Panel value="prompts" pt="md">
					<PromptsTab />
				</Tabs.Panel>
			</Tabs>
		</Container>
	);
}

export const AdminAIQuality = {
	route: "/admin/ai-quality",
	Page,
};
