import { useEffect, useState } from "react";
import {
	ActionIcon,
	Badge,
	Box,
	Button,
	Card,
	CopyButton,
	Divider,
	Grid,
	Group,
	Modal,
	Stack,
	Table,
	Text,
	ThemeIcon,
	Tooltip,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
	IconBrandTelegram,
	IconBrandWhatsapp,
	IconCheck,
	IconCopy,
	IconGift,
	IconRefresh,
	IconShare,
} from "@tabler/icons-react";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import { InnerPage } from "@shared/ui/InnerPage";
import { shadows, radii } from "@app/styles/theme";
import {
	$isLoadingReferrals,
	$isRegenerating,
	$referralOverview,
} from "../../model/stores";
import {
	fetchReferralOverviewFx,
	regenerateReferralCodeFx,
} from "../../model/effects";
import { useTelegramBackClose } from "@shared/hooks/useTelegramBackClose";

/**
 * PR-T — phase-2 referral program cabinet page.
 *
 * Three sections, top-to-bottom:
 *   1. Hero — code + share helpers (copy, Telegram, WhatsApp, native share).
 *   2. Stats grid — invited / qualified / total rewards.
 *   3. Recent events table — latest 20 attribution rows.
 *
 * The page is intentionally read-mostly; the only mutating action is
 * "Regenerate code", gated behind a confirm modal because rotating
 * invalidates the user's outstanding share links.
 */
function Page() {
	const { t } = useTranslation("seller");
	const [overview, isLoading, isRegenerating] = useUnit([
		$referralOverview,
		$isLoadingReferrals,
		$isRegenerating,
	]);
	const [confirmOpen, { open: openConfirm, close: closeConfirm }] =
		useDisclosure(false);
	useTelegramBackClose(confirmOpen, closeConfirm);
	const [regenError, setRegenError] = useState<string | null>(null);

	useEffect(() => {
		void fetchReferralOverviewFx();
	}, []);

	const handleRegenerate = async () => {
		setRegenError(null);
		try {
			await regenerateReferralCodeFx();
			closeConfirm();
		} catch (err: unknown) {
			// Surface 429 rate-limit copy in-place rather than a toast —
			// gives the user actionable context next to the button.
			const msg =
				(err as { response?: { data?: { detail?: { error?: string } } } })
					?.response?.data?.detail?.error ?? "error";
			setRegenError(msg);
		}
	};

	const code = overview?.referral_code ?? "";
	const shareUrl = overview?.share_url ?? "";
	const stats = overview?.stats;
	const events = overview?.recent_events ?? [];

	// UZS micros → whole UZS for display. Falls back to 0 on missing stats.
	const totalRewardsUzs = stats
		? Math.floor((stats.total_rewards_micros || 0) / 1_000_000)
		: 0;

	const handleNativeShare = async () => {
		if (!shareUrl) return;
		// `navigator.share` requires a user gesture + HTTPS. Falls back to
		// no-op when unavailable — the explicit Telegram/WhatsApp buttons
		// cover that case.
		if (typeof navigator !== "undefined" && navigator.share) {
			try {
				await navigator.share({
					title: t("referrals.title", "Реферальная программа"),
					text: t("referrals.shareCta", "Присоединяйся к PANA!"),
					url: shareUrl,
				});
			} catch {
				// Cancellation throws — ignore silently.
			}
		}
	};

	const telegramShareUrl = shareUrl
		? `https://t.me/share/url?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(
				t("referrals.shareCta", "Присоединяйся к PANA!"),
			)}`
		: "";
	const whatsappShareUrl = shareUrl
		? `https://wa.me/?text=${encodeURIComponent(
				`${t("referrals.shareCta", "Присоединяйся к PANA!")} ${shareUrl}`,
			)}`
		: "";

	return (
		<InnerPage title={t("referrals.title", "Реферальная программа")} noPadding>
			<Box p="md">
				<Stack gap="md">
					{/* ── Hero card ── */}
					<Card
						radius={radii.md}
						p="lg"
						style={{
							background:
								"linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)",
							border: "1px solid #fcd34d",
							boxShadow: shadows.md,
						}}
					>
						<Stack gap="md">
							<Group gap="sm" wrap="nowrap">
								<ThemeIcon
									size={42}
									radius="md"
									variant="white"
									color="yellow"
								>
									<IconGift size={22} />
								</ThemeIcon>
								<Box>
									<Text fw={700} size="md" c="#78350f">
										{t("referrals.title", "Реферальная программа")}
									</Text>
									<Text size="xs" c="#92400e" mt={2}>
										{t(
											"referrals.shareCta",
											"Присоединяйся к PANA!",
										)}
									</Text>
								</Box>
							</Group>

							<Box>
								<Text size="xs" c="#92400e" fw={600} mb={4}>
									{t("referrals.code", "Ваш код")}
								</Text>
								<Group gap="xs" wrap="nowrap">
									<Card
										radius="sm"
										p="sm"
										style={{
											background: "rgba(255,255,255,0.85)",
											flex: 1,
											textAlign: "center",
											fontFamily: "monospace",
											fontWeight: 700,
											fontSize: 18,
											letterSpacing: 2,
											color: "#78350f",
										}}
									>
										{code || "—"}
									</Card>
									<CopyButton value={shareUrl} timeout={1500}>
										{({ copied, copy }) => (
											<Tooltip
												label={
													copied
														? t("referrals.copied", "Скопировано")
														: t("referrals.copy", "Скопировать ссылку")
												}
											>
												<ActionIcon
													size="lg"
													variant="filled"
													color="yellow"
													onClick={copy}
													disabled={!shareUrl}
												>
													{copied ? (
														<IconCheck size={18} />
													) : (
														<IconCopy size={18} />
													)}
												</ActionIcon>
											</Tooltip>
										)}
									</CopyButton>
								</Group>
							</Box>

							<Group gap="xs" grow>
								<Button
									component="a"
									href={telegramShareUrl || undefined}
									target="_blank"
									rel="noopener noreferrer"
									variant="white"
									color="blue"
									leftSection={<IconBrandTelegram size={16} />}
									disabled={!shareUrl}
								>
									Telegram
								</Button>
								<Button
									component="a"
									href={whatsappShareUrl || undefined}
									target="_blank"
									rel="noopener noreferrer"
									variant="white"
									color="green"
									leftSection={<IconBrandWhatsapp size={16} />}
									disabled={!shareUrl}
								>
									WhatsApp
								</Button>
								{typeof navigator !== "undefined" && "share" in navigator && (
									<Button
										variant="white"
										color="dark"
										leftSection={<IconShare size={16} />}
										onClick={handleNativeShare}
										disabled={!shareUrl}
									>
										{t("referrals.shareSystem", "Поделиться")}
									</Button>
								)}
							</Group>
						</Stack>
					</Card>

					{/* ── Stats grid ── */}
					<Grid gutter="sm">
						<Grid.Col span={4}>
							<Card
								radius={radii.md}
								p="sm"
								style={{
									background: "#eff6ff",
									border: "1px solid #dbeafe",
									boxShadow: shadows.sm,
								}}
							>
								<Text size="xs" c="dimmed" fw={600}>
									{t("referrals.stats.invited", "Приглашено")}
								</Text>
								<Text size="xl" fw={700} c="#1d4ed8" mt={4}>
									{stats?.invited_count ?? 0}
								</Text>
							</Card>
						</Grid.Col>
						<Grid.Col span={4}>
							<Card
								radius={radii.md}
								p="sm"
								style={{
									background: "#ecfdf5",
									border: "1px solid #d1fae5",
									boxShadow: shadows.sm,
								}}
							>
								<Text size="xs" c="dimmed" fw={600}>
									{t("referrals.stats.qualified", "Квалифицировано")}
								</Text>
								<Text size="xl" fw={700} c="#047857" mt={4}>
									{stats?.qualified_count ?? 0}
								</Text>
							</Card>
						</Grid.Col>
						<Grid.Col span={4}>
							<Card
								radius={radii.md}
								p="sm"
								style={{
									background: "#fef3c7",
									border: "1px solid #fde68a",
									boxShadow: shadows.sm,
								}}
							>
								<Text size="xs" c="dimmed" fw={600}>
									{t("referrals.stats.rewards", "Награды (сум)")}
								</Text>
								<Text size="lg" fw={700} c="#78350f" mt={4}>
									{totalRewardsUzs.toLocaleString("ru-RU")}
								</Text>
							</Card>
						</Grid.Col>
					</Grid>

					{/* ── Recent events table ── */}
					<Card
						radius={radii.md}
						p="md"
						style={{
							background: "#ffffff",
							border: "1px solid #f1f5f9",
							boxShadow: shadows.sm,
						}}
					>
						<Stack gap="sm">
							<Text fw={700} size="sm">
								{t("referrals.recentTitle", "Недавняя активность")}
							</Text>
							{events.length === 0 && !isLoading && (
								<Text size="sm" c="dimmed">
									{t(
										"referrals.recentEmpty",
										"Пока никто не присоединился по вашей ссылке.",
									)}
								</Text>
							)}
							{events.length > 0 && (
								<Table striped style={{ fontSize: 12 }}>
									<Table.Thead>
										<Table.Tr>
											<Table.Th>{t("referrals.colUser", "Пользователь")}</Table.Th>
											<Table.Th>{t("referrals.colEvent", "Событие")}</Table.Th>
											<Table.Th>{t("referrals.colDate", "Дата")}</Table.Th>
										</Table.Tr>
									</Table.Thead>
									<Table.Tbody>
										{events.map((evt, idx) => (
											<Table.Tr key={`${evt.referred_user_id}-${evt.event_type}-${idx}`}>
												<Table.Td style={{ fontFamily: "monospace" }}>
													{evt.referred_user_id.slice(0, 8)}…
												</Table.Td>
												<Table.Td>
													<Badge
														size="xs"
														variant="light"
														color={
															evt.event_type === "rewarded"
																? "yellow"
																: evt.event_type === "qualified"
																	? "green"
																	: "blue"
														}
													>
														{t(
															`referrals.event.${evt.event_type}`,
															evt.event_type,
														)}
													</Badge>
												</Table.Td>
												<Table.Td>
													{new Date(evt.created_at).toLocaleDateString("ru-RU")}
												</Table.Td>
											</Table.Tr>
										))}
									</Table.Tbody>
								</Table>
							)}
						</Stack>
					</Card>

					<Divider />

					{/* ── Regenerate ── */}
					<Group justify="flex-end">
						<Button
							variant="subtle"
							color="red"
							leftSection={<IconRefresh size={14} />}
							onClick={openConfirm}
							disabled={isLoading}
						>
							{t("referrals.regenerate", "Сгенерировать новый код")}
						</Button>
					</Group>
				</Stack>
			</Box>

			<Modal
				opened={confirmOpen}
				onClose={closeConfirm}
				title={t("referrals.regenerate", "Сгенерировать новый код")}
				centered
			>
				<Stack gap="md">
					<Text size="sm">
						{t(
							"referrals.confirmRegenerate",
							"Старая ссылка перестанет работать. Продолжить?",
						)}
					</Text>
					{regenError && (
						<Text size="xs" c="red">
							{regenError === "rate_limited"
								? t(
										"referrals.errorRateLimited",
										"Можно обновлять только раз в сутки.",
									)
								: t("referrals.errorGeneric", "Не удалось обновить код.")}
						</Text>
					)}
					<Group justify="flex-end" gap="xs">
						<Button variant="subtle" onClick={closeConfirm}>
							{t("common.cancel", "Отмена")}
						</Button>
						<Button
							color="red"
							onClick={handleRegenerate}
							loading={isRegenerating}
						>
							{t("referrals.regenerate", "Сгенерировать новый код")}
						</Button>
					</Group>
				</Stack>
			</Modal>
		</InnerPage>
	);
}

export const SellerReferrals = {
	route: "/seller/referrals",
	Page,
};
