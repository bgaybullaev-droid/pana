/**
 * Block phase-2 — seller "Boost" purchase modal.
 *
 * Three tabs / cards (urgent / notify-priority / boost). Each card has
 * a confirm button that calls the matching endpoint. A 402 from the
 * backend flips the modal to a "Top up wallet" CTA.
 */

import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
	Modal,
	Stack,
	Text,
	Group,
	Button,
	Card,
	Badge,
	NumberInput,
	Alert,
	Tabs,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconBolt, IconBellRinging, IconArrowUp, IconAlertCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import {
	buyPromotionFx,
	InsufficientFundsError,
	PROMOTION_PRICES_UZS,
	PROMOTION_DEFAULT_DAYS,
	type PromotionKind,
} from "../model";

interface BoostModalProps {
	listingId: string | null;
	opened: boolean;
	onClose: () => void;
}

function formatUzs(amount: number): string {
	return new Intl.NumberFormat("ru-RU").format(amount) + " UZS";
}

export function BoostModal({ listingId, opened, onClose }: BoostModalProps) {
	const { t } = useTranslation("seller");
	const navigate = useNavigate();
	const [tab, setTab] = useState<PromotionKind>("urgent");
	const [days, setDays] = useState<number>(PROMOTION_DEFAULT_DAYS.urgent);
	const [loading, setLoading] = useState(false);
	const [insufficient, setInsufficient] = useState(false);

	const handleTabChange = (kind: PromotionKind) => {
		setTab(kind);
		setDays(PROMOTION_DEFAULT_DAYS[kind]);
		setInsufficient(false);
	};

	const handleClose = () => {
		setInsufficient(false);
		onClose();
	};

	const totalPrice =
		tab === "boost"
			? PROMOTION_PRICES_UZS.boost * days
			: PROMOTION_PRICES_UZS[tab];

	const handlePurchase = useCallback(async () => {
		if (!listingId) return;
		setLoading(true);
		setInsufficient(false);
		try {
			const result = await buyPromotionFx({
				listing_id: listingId,
				kind: tab,
				duration_days: days,
			});
			notifications.show({
				title: t("promotions.purchase"),
				message: t("promotions.purchaseSuccess", {
					until: new Date(result.active_until).toLocaleDateString(),
				}),
				color: "green",
			});
			onClose();
		} catch (err) {
			if (err instanceof InsufficientFundsError) {
				setInsufficient(true);
			} else {
				notifications.show({
					title: t("notifications.error", { defaultValue: "Error" }),
					message: (err as Error)?.message || "Failed",
					color: "red",
				});
			}
		} finally {
			setLoading(false);
		}
	}, [listingId, tab, days, t, onClose]);

	const handleTopUp = () => {
		onClose();
		// Wallet route may not exist yet -> tariffs as fallback.
		navigate("/seller/tariffs");
	};

	const tabConfig: Record<
		PromotionKind,
		{ icon: typeof IconBolt; color: string; labelKey: string; priceKey: string }
	> = {
		urgent: {
			icon: IconBolt,
			color: "orange",
			labelKey: "promotions.urgent.label",
			priceKey: "promotions.urgent.price",
		},
		notify_priority: {
			icon: IconBellRinging,
			color: "blue",
			labelKey: "promotions.notifyPriority.label",
			priceKey: "promotions.notifyPriority.price",
		},
		boost: {
			icon: IconArrowUp,
			color: "violet",
			labelKey: "promotions.boost.label",
			priceKey: "promotions.boost.price",
		},
	};

	return (
		<Modal
			opened={opened}
			onClose={handleClose}
			title={<Text fw={700}>{t("promotions.purchase")}</Text>}
			centered
			radius="md"
			size="md"
		>
			<Stack gap="md">
				<Tabs
					value={tab}
					onChange={(v) => handleTabChange((v ?? "urgent") as PromotionKind)}
				>
					<Tabs.List grow>
						{(Object.keys(tabConfig) as PromotionKind[]).map((k) => {
							const Icon = tabConfig[k].icon;
							return (
								<Tabs.Tab key={k} value={k} leftSection={<Icon size={14} />}>
									{t(tabConfig[k].labelKey)}
								</Tabs.Tab>
							);
						})}
					</Tabs.List>
				</Tabs>

				<Card withBorder radius="md" padding="md">
					<Stack gap="xs">
						<Group justify="space-between">
							<Text fw={600}>{t(tabConfig[tab].labelKey)}</Text>
							<Badge color={tabConfig[tab].color} variant="light">
								{formatUzs(totalPrice)}
							</Badge>
						</Group>
						<Text size="sm" c="dimmed">
							{t(tabConfig[tab].priceKey)}
						</Text>
						<NumberInput
							label={t("promotions.durationDays", { defaultValue: "Days" })}
							value={days}
							onChange={(v) => setDays(Number(v) || 1)}
							min={1}
							max={tab === "boost" ? 14 : tab === "notify_priority" ? 90 : 30}
						/>
					</Stack>
				</Card>

				{insufficient && (
					<Alert
						color="red"
						icon={<IconAlertCircle size={16} />}
						title={t("promotions.insufficientFunds")}
					>
						<Group justify="space-between" mt="xs">
							<Button variant="subtle" onClick={handleClose}>
								{t("listings.cancel", { defaultValue: "Cancel" })}
							</Button>
							<Button color="orange" onClick={handleTopUp}>
								{t("promotions.topUp", { defaultValue: "Top up wallet" })}
							</Button>
						</Group>
					</Alert>
				)}

				{!insufficient && (
					<Group justify="flex-end" gap="sm">
						<Button variant="default" onClick={handleClose}>
							{t("listings.cancel", { defaultValue: "Cancel" })}
						</Button>
						<Button
							loading={loading}
							onClick={handlePurchase}
							color={tabConfig[tab].color}
						>
							{t("promotions.confirm", { defaultValue: "Confirm" })} ·{" "}
							{formatUzs(totalPrice)}
						</Button>
					</Group>
				)}
			</Stack>
		</Modal>
	);
}
