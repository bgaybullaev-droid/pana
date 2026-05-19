/**
 * Block phase-2 — admin analytics (price-index) page.
 *
 * Renders a small filter form (district / property type / rooms /
 * window) and a result card with the USD-equivalent median + IQR +
 * sample size returned by ``GET /analytics/price-index``. The
 * insufficient-sample case (sample_size < 5) is rendered as a hint
 * rather than a misleading number — the backend already returns
 * ``median: null`` in that case.
 */

import { useState } from "react";
import {
	Container,
	Stack,
	Title,
	Text,
	Group,
	TextInput,
	Select,
	NumberInput,
	Button,
	Card,
	Loader,
	Badge,
	SimpleGrid,
} from "@mantine/core";
import { IconChartLine, IconSearch } from "@tabler/icons-react";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";

import {
	$priceIndex,
	fetchPriceIndexFx,
	type PriceIndexQuery,
} from "../../model";

function Page() {
	const { t } = useTranslation("admin");
	const result = useUnit($priceIndex);
	const loading = useUnit(fetchPriceIndexFx.pending);

	const [district, setDistrict] = useState("");
	const [propertyType, setPropertyType] = useState<string | null>(null);
	const [rooms, setRooms] = useState<number | "">("");
	const [windowDays, setWindowDays] = useState<number | "">(180);

	const apply = () => {
		const query: PriceIndexQuery = {};
		if (district.trim()) query.district = district.trim();
		if (propertyType) {
			query.property_type = propertyType as PriceIndexQuery["property_type"];
		}
		if (typeof rooms === "number") query.rooms = rooms;
		if (typeof windowDays === "number") query.window_days = windowDays;
		void fetchPriceIndexFx(query);
	};

	const formatUsd = (n: number) =>
		new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(n);

	return (
		<Container size={1000} py="md">
			<Stack gap="sm" mb="md">
				<Group gap="xs">
					<IconChartLine size={22} color="#4f46e5" />
					<Title order={2}>{t("analytics.title")}</Title>
				</Group>
				<Text size="sm" c="dimmed">
					{t("analytics.subtitle")}
				</Text>
			</Stack>

			<Card withBorder radius="md" mb="md">
				<SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="sm">
					<TextInput
						label={t("analytics.districtLabel")}
						placeholder={t("analytics.districtPlaceholder")}
						value={district}
						onChange={(e) => setDistrict(e.currentTarget.value)}
					/>
					<Select
						label={t("analytics.propertyTypeLabel")}
						placeholder={t("analytics.propertyTypeAny")}
						value={propertyType}
						onChange={setPropertyType}
						clearable
						data={[
							{ value: "apartment", label: t("analytics.types.apartment") },
							{ value: "house", label: t("analytics.types.house") },
							{ value: "commercial", label: t("analytics.types.commercial") },
							{ value: "land", label: t("analytics.types.land") },
						]}
					/>
					<NumberInput
						label={t("analytics.roomsLabel")}
						placeholder={t("analytics.roomsAny")}
						value={rooms}
						onChange={(v) => setRooms(typeof v === "number" ? v : "")}
						min={0}
						max={20}
						hideControls
					/>
					<NumberInput
						label={t("analytics.windowLabel")}
						value={windowDays}
						onChange={(v) => setWindowDays(typeof v === "number" ? v : "")}
						min={1}
						max={3650}
						hideControls
					/>
				</SimpleGrid>
				<Group justify="flex-end" mt="md">
					<Button
						leftSection={<IconSearch size={16} />}
						onClick={apply}
						loading={loading}
					>
						{t("analytics.apply")}
					</Button>
				</Group>
			</Card>

			{loading && <Loader />}

			{!loading && result && (
				<Card withBorder radius="md">
					<Stack gap="xs">
						<Group justify="space-between">
							<Text fw={700} size="lg">
								{t("analytics.medianLabel")}
							</Text>
							<Badge variant="light" color="indigo">
								{t("analytics.sampleSize", {
									count: result.sample_size,
								})}
							</Badge>
						</Group>
						{result.median === null ? (
							<Text c="dimmed" size="sm">
								{t("analytics.insufficient")}
							</Text>
						) : (
							<>
								<Text size="2rem" fw={800} c="indigo">
									${formatUsd(result.median)}
								</Text>
								<Group gap="lg">
									<Text size="sm" c="dimmed">
										{t("analytics.p25")}:{" "}
										<Text component="span" fw={600} c="dark">
											${formatUsd(result.p25 ?? 0)}
										</Text>
									</Text>
									<Text size="sm" c="dimmed">
										{t("analytics.p75")}:{" "}
										<Text component="span" fw={600} c="dark">
											${formatUsd(result.p75 ?? 0)}
										</Text>
									</Text>
								</Group>
								<Text size="xs" c="dimmed">
									{t("analytics.windowFooter", {
										days: result.window_days,
									})}
								</Text>
							</>
						)}
					</Stack>
				</Card>
			)}
		</Container>
	);
}

export const AdminAnalytics = {
	route: "/admin/analytics",
	Page,
};
