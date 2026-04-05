import { useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
	Stack,
	Text,
	Box,
	Group,
	Loader,
	Center,
	Avatar,
	Button,
	UnstyledButton,
} from "@mantine/core";
import {
	IconBell,
	IconHome,
	IconHeart,
	IconTag,
	IconMessage,
	IconChecks,
} from "@tabler/icons-react";
import { InnerPage } from "@shared/ui/InnerPage";
import { formatTimeAgo } from "@shared/lib/date";
import { notificationsApi } from "@shared/api/notifications";
import { useAuth } from "@app/providers/useAuth";
import { UnauthScreen } from "@shared/ui/UnauthScreen";
import type { Notification } from "@shared/api/types";
import { radii } from "@app/styles/theme";

// Group notifications by date
function groupByDate(
	notifications: Notification[],
	t: (key: string) => string,
): { label: string; items: Notification[] }[] {
	const now = new Date();
	const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
	const yesterday = new Date(today.getTime() - 86400000);

	const groups: Record<string, Notification[]> = {};
	const order: string[] = [];

	for (const n of notifications) {
		const date = new Date(n.created_at);
		const dateStart = new Date(
			date.getFullYear(),
			date.getMonth(),
			date.getDate(),
		);

		let label: string;
		if (dateStart.getTime() === today.getTime()) {
			label = t("notifications.today");
		} else if (dateStart.getTime() === yesterday.getTime()) {
			label = t("notifications.yesterday");
		} else {
			label = t("notifications.earlier");
		}

		if (!groups[label]) {
			groups[label] = [];
			order.push(label);
		}
		groups[label].push(n);
	}

	return order.map((label) => ({ label, items: groups[label] }));
}

const ICON_CONFIG: Record<
	string,
	{ icon: typeof IconBell; color: string; bg: string }
> = {
	comment_reply: { icon: IconMessage, color: "#228be6", bg: "#e7f5ff" },
	price_drop: { icon: IconTag, color: "#40c057", bg: "#ebfbee" },
	new_listing: { icon: IconHome, color: "#ff922b", bg: "#fff4e6" },
	favorite_update: { icon: IconHeart, color: "#ff6b6b", bg: "#fff5f5" },
};

// TODO: Remove mock data before production
const MOCK_NOTIFICATIONS: Notification[] = [
	{
		id: "mock-1",
		user_id: "mock",
		type: "price_drop",
		title: "Цена снижена!",
		message: "Квартира в Мирабадском районе подешевела на $5,000 — теперь $85,000",
		listing_id: null,
		comment_id: null,
		actor: null,
		read: false,
		created_at: new Date().toISOString(),
	},
	{
		id: "mock-2",
		user_id: "mock",
		type: "new_listing",
		title: "Новое объявление",
		message: "Появилась 3-комнатная квартира в Юнусабадском районе за $120,000",
		listing_id: null,
		comment_id: null,
		actor: null,
		read: false,
		created_at: new Date(Date.now() - 3600000).toISOString(),
	},
	{
		id: "mock-3",
		user_id: "mock",
		type: "comment_reply",
		title: "Ответ на комментарий",
		message: "Продавец ответил на ваш вопрос: «Да, возможен торг»",
		listing_id: null,
		comment_id: null,
		actor: {
			id: "seller-1",
			first_name: "Алишер",
			last_name: "Каримов",
			username: "alisher_k",
			avatar_url: null,
		},
		read: true,
		created_at: new Date(Date.now() - 86400000).toISOString(),
	},
	{
		id: "mock-4",
		user_id: "mock",
		type: "favorite_update",
		title: "Обновление избранного",
		message: "Дом в Чиланзарском районе был обновлён — добавлены новые фото",
		listing_id: null,
		comment_id: null,
		actor: null,
		read: true,
		created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
	},
	{
		id: "mock-5",
		user_id: "mock",
		type: "new_listing",
		title: "Подходящее объявление",
		message: "Участок 10 соток в Ташкентской области за $20,000 — совпадает с вашими предпочтениями",
		listing_id: null,
		comment_id: null,
		actor: null,
		read: true,
		created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
	},
];

function Page() {
	const { t } = useTranslation("buyer");
	const navigate = useNavigate();
	const { isAuthenticated } = useAuth();
	const [notifications, setNotifications] = useState<Notification[]>(MOCK_NOTIFICATIONS);
	const [isLoading, setIsLoading] = useState(false);
	const [unreadCount, setUnreadCount] = useState(MOCK_NOTIFICATIONS.filter((n) => !n.read).length);
	const [page, setPage] = useState(1);
	const [hasMore, setHasMore] = useState(true);
	// TODO: Re-enable after removing mock data
	// const initializedRef = useRef(false);

	const loadNotifications = useCallback(
		async (pageNum: number, reset = false) => {
			setIsLoading(true);
			try {
				const response = await notificationsApi.getNotifications(pageNum);
				setNotifications((prev) =>
					reset ? response.items : [...prev, ...response.items],
				);
				setHasMore(response.page < response.total_pages);
				setPage(pageNum);

				const countResponse = await notificationsApi.getUnreadCount();
				setUnreadCount(countResponse.unread_count);
			} catch (error) {
				console.error("Failed to load notifications:", error);
			} finally {
				setIsLoading(false);
			}
		},
		[],
	);

	// TODO: Re-enable API call after removing mock data
	// useEffect(() => {
	// 	if (!isAuthenticated) return;
	// 	if (initializedRef.current) return;
	// 	initializedRef.current = true;
	// 	loadNotifications(1, true);
	// }, [isAuthenticated, loadNotifications]);

	const handleMarkAllAsRead = () => {
		// TODO: Re-enable API call after removing mock data
		// notificationsApi.markAsRead();
		setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
		setUnreadCount(0);
	};

	const handleNotificationClick = async (notification: Notification) => {
		if (!notification.read) {
			try {
				await notificationsApi.markAsRead([notification.id]);
				setNotifications((prev) =>
					prev.map((n) =>
						n.id === notification.id ? { ...n, read: true } : n,
					),
				);
				setUnreadCount((prev) => Math.max(0, prev - 1));
			} catch (error) {
				console.error("Failed to mark notification as read:", error);
			}
		}

		if (notification.listing_id) {
			navigate(`/listings/${notification.listing_id}`);
		}
	};

	const handleLoadMore = () => {
		if (!isLoading && hasMore) {
			loadNotifications(page + 1);
		}
	};

	const groupedNotifications = useMemo(
		() => groupByDate(notifications, t),
		[notifications, t],
	);

	if (!isAuthenticated) {
		return (
			<UnauthScreen
				icon={IconBell}
				title={t("notifications.title")}
				subtitle={t("notifications.subtitle")}
				loginPrompt={t("notifications.loginPrompt")}
				loginLabel={t("common.login")}
				onLogin={() => navigate("/auth")}
				loginVariant="link"
			/>
		);
	}

	return (
		<InnerPage
			title={t("notifications.title")}
			badge={
				unreadCount > 0 ? (
					<Box
						style={{
							backgroundColor: "#ff6b6b",
							borderRadius: radii.md,
							padding: "2px 8px",
							minWidth: 22,
							textAlign: "center",
						}}
					>
						<Text
							style={{
								fontSize: 11,
								fontWeight: 700,
								color: "white",
								lineHeight: 1.4,
							}}
						>
							{unreadCount}
						</Text>
					</Box>
				) : undefined
			}
			actions={
				<UnstyledButton
					onClick={unreadCount > 0 ? handleMarkAllAsRead : undefined}
					style={{ display: "flex", alignItems: "center", cursor: unreadCount > 0 ? "pointer" : "default" }}
				>
					<IconChecks size={22} color={unreadCount > 0 ? "#228be6" : "#adb5bd"} stroke={1.8} />
				</UnstyledButton>
			}
		>
				{isLoading && notifications.length === 0 ? (
					<Center py={48}>
						<Loader size="md" color="blue" />
					</Center>
				) : notifications.length === 0 ? (
					<Box ta="center" py={48}>
						<Box
							style={{
								width: 80,
								height: 80,
								borderRadius: radii.full,
								backgroundColor: "#e7f5ff",
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								margin: "0 auto 16px",
							}}
						>
							<IconBell size={36} color="#74c0fc" stroke={1.5} />
						</Box>
						<Text fw={600} size="md">
							{t("notifications.emptyTitle")}
						</Text>
						<Text c="dimmed" size="sm" mt={4}>
							{t("notifications.emptyDescription")}
						</Text>
					</Box>
				) : (
					<Stack gap="lg">
						{groupedNotifications.map((group) => (
							<Box key={group.label}>
								{/* Date section header */}
								<Text
									size="xs"
									fw={700}
									c="dimmed"
									tt="uppercase"
									mb={8}
									ml={4}
								>
									{group.label}
								</Text>

								<Stack gap={8}>
									{group.items.map((notification) => {
										const config = ICON_CONFIG[notification.type] || {
											icon: IconBell,
											color: "#868e96",
											bg: "#f1f3f5",
										};
										const Icon = config.icon;

										return (
											<UnstyledButton
												key={notification.id}
												onClick={() => handleNotificationClick(notification)}
												style={{ display: "block" }}
											>
												<Box
													style={{
														backgroundColor: notification.read
															? "#f8f9fa"
															: "white",
														borderRadius: radii.md,
														padding: "12px 14px",
														boxShadow: notification.read
															? "none"
															: "0 2px 8px rgba(0,0,0,0.04), 0 4px 16px rgba(0,0,0,0.04)",
														borderLeft: notification.read
															? "3px solid transparent"
															: `3px solid ${config.color}`,
														transition: "all 0.2s ease",
													}}
												>
													<Group wrap="nowrap" gap={12}>
														{notification.actor ? (
															<Avatar
																src={notification.actor.avatar_url}
																size={42}
																radius="xl"
																color="blue"
																style={{ flexShrink: 0 }}
															>
																{notification.actor.first_name[0]}
															</Avatar>
														) : (
															<Box
																style={{
																	width: 42,
																	height: 42,
																	borderRadius: radii.md,
																	backgroundColor: config.bg,
																	display: "flex",
																	alignItems: "center",
																	justifyContent: "center",
																	flexShrink: 0,
																}}
															>
																<Icon
																	size={20}
																	color={config.color}
																	stroke={2}
																/>
															</Box>
														)}
														<Box style={{ flex: 1, minWidth: 0 }}>
															<Group
																justify="space-between"
																wrap="nowrap"
																mb={2}
															>
																<Text
																	size="sm"
																	fw={notification.read ? 500 : 700}
																	truncate
																	c={notification.read ? "gray.7" : "dark.8"}
																>
																	{notification.title}
																</Text>
																<Text
																	size="xs"
																	c="dimmed"
																	style={{ flexShrink: 0, fontSize: 11 }}
																>
																	{formatTimeAgo(notification.created_at)}
																</Text>
															</Group>
															<Text
																size="xs"
																c={notification.read ? "gray.5" : "gray.6"}
																lineClamp={2}
																style={{ lineHeight: 1.4 }}
															>
																{notification.message}
															</Text>
														</Box>
													</Group>
												</Box>
											</UnstyledButton>
										);
									})}
								</Stack>
							</Box>
						))}

						{hasMore && (
							<Center>
								<Button
									variant="subtle"
									onClick={handleLoadMore}
									loading={isLoading}
									radius={10}
								>
									{t("notifications.loadMore")}
								</Button>
							</Center>
						)}
					</Stack>
				)}
		</InnerPage>
	);
}

export const Notifications = {
	route: "/notifications",
	Page,
};
