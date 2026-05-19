import { useEffect, useState } from "react";
import {
	Box,
	Container,
	Stack,
	Text,
	Group,
	Button,
	Card,
	Progress,
	Collapse,
	Modal,
	Skeleton,
	ThemeIcon,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
	IconCheck,
	IconHome,
	IconCrown,
	IconChevronDown,
	IconChevronUp,
	IconInfoCircle,
} from "@tabler/icons-react";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import { InnerPage } from "@shared/ui/InnerPage";
import { formatNumber } from "@shared/lib/formatNumber";
import { radii, shadows } from "@app/styles/theme";
import {
	$tariffsStatus,
	$isLoadingTariffs,
	$tariffsError,
} from "../../model/stores";
import { fetchTariffsStatusFx } from "../../model/effects";

function Page() {
	const { t } = useTranslation("seller");
	const [tariffs, isLoading, error] = useUnit([
		$tariffsStatus,
		$isLoadingTariffs,
		$tariffsError,
	]);
	const [
		detailsOpened,
		{ toggle: toggleDetails },
	] = useDisclosure(false);
	const [
		modalOpened,
		{ open: openModal, close: closeModal },
	] = useDisclosure(false);

	useEffect(() => {
		if (!tariffs && !isLoading) {
			void fetchTariffsStatusFx();
		}
	}, [tariffs, isLoading]);

	const showProgress = tariffs && tariffs.test_period_active;

	const listingProgress =
		tariffs && tariffs.trigger_listings > 0
			? Math.min(
					100,
					(tariffs.current_listings_total / tariffs.trigger_listings) * 100,
				)
			: 0;
	const daysProgress =
		tariffs && tariffs.trigger_days > 0
			? Math.min(100, (tariffs.days_elapsed / tariffs.trigger_days) * 100)
			: 0;

	return (
		<InnerPage title={t("tariffs.pageTitle")} noPadding>
			<Container px="md" py="md">
				<Stack gap={16}>
					{error && !tariffs ? (
						<Card
							padding="md"
							style={{
								background: "#fef2f2",
								border: "1px solid #fecaca",
								borderRadius: radii.md,
							}}
						>
							<Stack gap={8} align="center">
								<ThemeIcon
									size={36}
									radius="xl"
									variant="light"
									color="red"
								>
									<IconInfoCircle size={20} />
								</ThemeIcon>
								<Text size="sm" fw={600} c="#991b1b" ta="center">
									{t("listings.loadErrorTitle")}
								</Text>
								<Text size="xs" c="#7f1d1d" ta="center">
									{t("listings.loadErrorDesc")}
								</Text>
								<Button
									size="xs"
									variant="light"
									color="red"
									onClick={() => fetchTariffsStatusFx()}
								>
									{t("listings.reloadBtn")}
								</Button>
							</Stack>
						</Card>
					) : isLoading || !tariffs ? (
						<>
							<Skeleton height={120} radius={12} />
							<Skeleton height={200} radius={12} />
							<Skeleton height={200} radius={12} />
						</>
					) : (
						<>
							{/* Hero banner — test-period state */}
							<Card
								padding="md"
								style={{
									background:
										"linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)",
									border: "1px solid #fcd34d",
									borderRadius: radii.md,
								}}
							>
								<Group wrap="nowrap" align="flex-start" gap={12}>
									<ThemeIcon
										size={36}
										radius="xl"
										variant="filled"
										color="orange"
									>
										<IconInfoCircle size={20} />
									</ThemeIcon>
									<Box style={{ flex: 1 }}>
										<Text fw={700} size="md" c="#78350f" mb={4}>
											{t("tariffs.heroBanner")}
										</Text>
										<Text
											size="sm"
											c="#92400e"
											style={{ lineHeight: 1.4 }}
										>
											{t("tariffs.heroSubtitle")}
										</Text>
									</Box>
								</Group>

								{/* Progress disclosure */}
								<Box mt={12}>
									<Group
										justify="space-between"
										style={{ cursor: "pointer" }}
										onClick={toggleDetails}
									>
										<Text size="sm" fw={600} c="#78350f">
											{t("tariffs.detailsToggle")}
										</Text>
										{detailsOpened ? (
											<IconChevronUp size={16} color="#78350f" />
										) : (
											<IconChevronDown size={16} color="#78350f" />
										)}
									</Group>
									<Collapse in={detailsOpened}>
										<Stack gap={8} mt={12}>
											<Box>
												<Group
													justify="space-between"
													mb={4}
												>
													<Text size="xs" c="#78350f" fw={500}>
														{t("tariffs.progress.listings", {
															current: formatNumber(
																tariffs.current_listings_total,
															),
															target: formatNumber(
																tariffs.trigger_listings,
															),
														})}
													</Text>
													<Text size="xs" c="#78350f" fw={600}>
														{Math.round(listingProgress)}%
													</Text>
												</Group>
												<Progress
													value={listingProgress}
													color="orange"
													size="sm"
												/>
											</Box>
											<Box>
												<Group
													justify="space-between"
													mb={4}
												>
													<Text size="xs" c="#78350f" fw={500}>
														{t("tariffs.progress.days", {
															current: tariffs.days_elapsed,
															target: tariffs.trigger_days,
														})}
													</Text>
													<Text size="xs" c="#78350f" fw={600}>
														{Math.round(daysProgress)}%
													</Text>
												</Group>
												<Progress
													value={daysProgress}
													color="orange"
													size="sm"
												/>
											</Box>
										</Stack>
									</Collapse>
								</Box>
							</Card>

							{/* Placement card — listings */}
							<Card
								padding="lg"
								style={{
									background: "#ffffff",
									border: "1px solid #e2e8f0",
									borderRadius: radii.md,
									boxShadow: shadows.sm,
								}}
							>
								<Group gap={10} mb={12} wrap="nowrap">
									<ThemeIcon
										size={32}
										radius="xl"
										variant="light"
										color="blue"
									>
										<IconHome size={18} />
									</ThemeIcon>
									<Text fw={700} size="md" c="dark.9">
										{t("tariffs.placement.title")}
									</Text>
								</Group>
								<Stack gap={8}>
									<Group gap={8} wrap="nowrap">
										<IconCheck size={16} color="#10b981" />
										<Text size="sm" c="dark.7" fw={500}>
											{t("tariffs.placement.line1", {
												free: tariffs.free_listings_per_seller,
											})}
										</Text>
									</Group>
									<Group gap={8} wrap="nowrap">
										<IconCheck size={16} color="#10b981" />
										<Text size="sm" c="dark.7" fw={500}>
											{t("tariffs.placement.line2", {
												price: formatNumber(
													tariffs.extra_listing_price_uzs,
												),
											})}
										</Text>
									</Group>
								</Stack>
								<Group justify="flex-end" mt={16}>
									<Button
										variant="light"
										color="blue"
										onClick={openModal}
										data-disabled-reason="test-period-active"
									>
										{t("tariffs.payButton")}
									</Button>
								</Group>
							</Card>

							{/* Cabinet subscription card */}
							<Card
								padding="lg"
								style={{
									background:
										"linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)",
									border: "1px solid #7dd3fc",
									borderRadius: radii.md,
									boxShadow: shadows.sm,
								}}
							>
								<Group gap={10} mb={12} wrap="nowrap">
									<ThemeIcon
										size={32}
										radius="xl"
										variant="light"
										color="cyan"
									>
										<IconCrown size={18} />
									</ThemeIcon>
									<Box style={{ flex: 1 }}>
										<Text fw={700} size="md" c="dark.9">
											{t("tariffs.cabinet.title")}
										</Text>
										<Text size="lg" fw={800} c="cyan.7" mt={2}>
											{t("tariffs.cabinet.price", {
												price: formatNumber(
													tariffs.cabinet_subscription_price_uzs,
												),
											})}
										</Text>
									</Box>
								</Group>
								<Stack gap={6}>
									<Group gap={8} wrap="nowrap">
										<IconCheck size={14} color="#0891b2" />
										<Text size="sm" c="dark.7">
											{t("tariffs.cabinet.featureBot")}
										</Text>
									</Group>
									<Group gap={8} wrap="nowrap">
										<IconCheck size={14} color="#0891b2" />
										<Text size="sm" c="dark.7">
											{t("tariffs.cabinet.featureAnalytics")}
										</Text>
									</Group>
									<Group gap={8} wrap="nowrap">
										<IconCheck size={14} color="#0891b2" />
										<Text size="sm" c="dark.7">
											{t("tariffs.cabinet.featureClients")}
										</Text>
									</Group>
									<Group gap={8} wrap="nowrap">
										<IconCheck size={14} color="#0891b2" />
										<Text size="sm" c="dark.7">
											{t("tariffs.cabinet.featurePriority")}
										</Text>
									</Group>
								</Stack>
								<Group justify="flex-end" mt={16}>
									<Button
										variant="filled"
										color="cyan"
										onClick={openModal}
									>
										{t("tariffs.subscribeButton")}
									</Button>
								</Group>
							</Card>

							{/* Footer notes */}
							<Box mt={4}>
								<Text size="xs" c="dimmed" ta="center" lh={1.5}>
									{t("tariffs.footerGrandfathering")}
								</Text>
								<Text size="xs" c="dimmed" ta="center" lh={1.5} mt={4}>
									{t("tariffs.footerFreeForever")}
								</Text>
							</Box>
						</>
					)}
				</Stack>
			</Container>

			{/* Disabled-CTA info modal */}
			<Modal
				opened={modalOpened}
				onClose={closeModal}
				title={t("tariffs.modalDisabledTitle")}
				centered
			>
				<Stack gap={12}>
					<Text size="sm" c="dark.7">
						{t("tariffs.modalDisabledBody")}
					</Text>
					<Group justify="flex-end">
						<Button variant="default" onClick={closeModal}>
							{t("tariffs.modalCloseBtn")}
						</Button>
					</Group>
				</Stack>
			</Modal>
		</InnerPage>
	);
}

export const SellerTariffs = {
	route: "/seller/tariffs",
	Page,
};
