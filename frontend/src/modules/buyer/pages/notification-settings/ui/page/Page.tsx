import { useState, useEffect, useRef, useCallback } from "react";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import {
	Stack,
	Text,
	Box,
	Group,
	Switch,
	Slider,
	Checkbox,
	Container,
	Loader,
	Center,
} from "@mantine/core";
import {
	IconBell,
	IconBellOff,
	IconClock,
	IconFilter,
	IconGauge,
} from "@tabler/icons-react";
import { InnerPage } from "@shared/ui/InnerPage";
import { useAuth } from "@app/providers/useAuth";
import { UnauthScreen } from "@shared/ui/UnauthScreen";
import { useNavigate } from "react-router-dom";
import { radii, shadows } from "@app/styles/theme";
import { notifications } from "@mantine/notifications";
import {
	$notificationSettings,
	$notificationSettingsLoading,
	fetchNotificationSettingsFx,
	saveNotificationSettingsFx,
} from "../../model";
import type { NotificationTimeWindow } from "@shared/api/types";

const TIME_WINDOWS: { value: NotificationTimeWindow; labelKey: string }[] = [
	{ value: "morning", labelKey: "notificationSettings.window.morning" },
	{ value: "afternoon", labelKey: "notificationSettings.window.afternoon" },
	{ value: "evening", labelKey: "notificationSettings.window.evening" },
];

/** Card wrapper reused for each settings section */
function SettingCard({
	icon: Icon,
	iconColor,
	iconBg,
	title,
	description,
	children,
}: {
	icon: typeof IconBell;
	iconColor: string;
	iconBg: string;
	title: string;
	description: string;
	children: React.ReactNode;
}) {
	return (
		<Box
			style={{
				backgroundColor: "#ffffff",
				borderRadius: radii.md,
				padding: "16px",
				boxShadow: shadows.md,
				border: "1px solid #e9ecef",
			}}
		>
			<Group gap={12} mb={14} align="flex-start">
				<Box
					style={{
						width: 40,
						height: 40,
						borderRadius: radii.md,
						backgroundColor: iconBg,
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						flexShrink: 0,
					}}
				>
					<Icon size={20} color={iconColor} stroke={2} />
				</Box>
				<Box>
					<Text size="sm" fw={700} c="dark.8" lh={1.3}>
						{title}
					</Text>
					<Text size="xs" c="dimmed" mt={2}>
						{description}
					</Text>
				</Box>
			</Group>
			{children}
		</Box>
	);
}

function Page() {
	const { t } = useTranslation("buyer");
	const navigate = useNavigate();
	const { isAuthenticated } = useAuth();
	const [settings, isLoading] = useUnit([
		$notificationSettings,
		$notificationSettingsLoading,
	]);

	// Local state mirrors the store
	const [paused, setPaused] = useState(settings.paused);
	const [dailyLimit, setDailyLimit] = useState(settings.daily_limit);
	const [timeWindows, setTimeWindows] = useState<NotificationTimeWindow[]>(
		settings.time_windows,
	);
	const [sources, setSources] = useState(settings.sources);

	const initializedRef = useRef(false);
	const debounceRef = useRef<ReturnType<typeof setTimeout>>();
	// Ref that always holds the latest state so the unmount-flush reads
	// fresh values instead of the stale closure from mount time.
	const latestRef = useRef({ paused, dailyLimit, timeWindows, sources });

	// Fetch on mount
	useEffect(() => {
		if (!isAuthenticated) return;
		fetchNotificationSettingsFx();
	}, [isAuthenticated]);

	// Sync from store whenever it updates (fetch response or save response).
	// No initializedRef guard — the previous "only once" logic caused the
	// bug: the effect fired with DEFAULT_NOTIFICATION_SETTINGS on first
	// render, set initialized=true, then SKIPPED the real API data when
	// it arrived. Auto-save won't cause loops because scheduleAutoSave
	// is only called from UI event handlers, not from setState.
	useEffect(() => {
		if (!settings) return;
		setPaused(settings.paused);
		setDailyLimit(settings.daily_limit);
		setTimeWindows(settings.time_windows);
		setSources(settings.sources);
		initializedRef.current = true;
	}, [settings]);

	// Keep latestRef in sync so the unmount-flush always reads current values.
	useEffect(() => {
		latestRef.current = { paused, dailyLimit, timeWindows, sources };
	}, [paused, dailyLimit, timeWindows, sources]);

	// Auto-save with debounce
	const doSave = useCallback(
		(overrides?: Partial<typeof settings>) => {
			const payload = {
				paused,
				daily_limit: dailyLimit,
				time_windows: timeWindows,
				sources,
				...overrides,
			};
			saveNotificationSettingsFx(payload).then(() => {
				notifications.show({
					message: t("notificationSettings.saved"),
					color: "green",
					autoClose: 2000,
				});
			});
		},
		[paused, dailyLimit, timeWindows, sources, t],
	);

	const scheduleAutoSave = useCallback(
		(overrides?: Partial<typeof settings>) => {
			if (!initializedRef.current) return;
			if (debounceRef.current) clearTimeout(debounceRef.current);
			debounceRef.current = setTimeout(() => doSave(overrides), 700);
		},
		[doSave],
	);

	// Flush on unmount — reads from latestRef so we never overwrite the
	// user's changes with stale default-state captured at mount time.
	useEffect(() => {
		return () => {
			if (debounceRef.current) {
				clearTimeout(debounceRef.current);
				// A debounce was pending → flush with the LATEST values.
				if (initializedRef.current) {
					const cur = latestRef.current;
					saveNotificationSettingsFx({
						paused: cur.paused,
						daily_limit: cur.dailyLimit,
						time_windows: cur.timeWindows,
						sources: cur.sources,
					});
				}
			}
			// If no debounce was pending, the last auto-save already
			// persisted the state — no redundant PUT needed.
		};
	}, []);

	const handlePausedChange = (val: boolean) => {
		setPaused(val);
		scheduleAutoSave({ paused: val });
	};

	const handleDailyLimitChange = (val: number) => {
		setDailyLimit(val);
		scheduleAutoSave({ daily_limit: val });
	};

	const toggleWindow = (win: NotificationTimeWindow) => {
		const next = timeWindows.includes(win)
			? timeWindows.filter((w) => w !== win)
			: [...timeWindows, win];
		setTimeWindows(next);
		scheduleAutoSave({ time_windows: next });
	};

	const toggleSource = (key: keyof typeof sources) => {
		const next = { ...sources, [key]: !sources[key] };
		setSources(next);
		scheduleAutoSave({ sources: next });
	};

	if (!isAuthenticated) {
		return (
			<UnauthScreen
				icon={IconBell}
				title={t("notificationSettings.title")}
				subtitle={t("notificationSettings.subtitle")}
				loginPrompt={t("favorites.searches.loginPrompt")}
				loginLabel={t("common.login")}
				onLogin={() => navigate("/auth")}
				onBack={() => navigate(-1)}
			/>
		);
	}

	if (isLoading && !initializedRef.current) {
		return (
			<InnerPage title={t("notificationSettings.title")}>
				<Center py={48}>
					<Loader size="md" color="blue" />
				</Center>
			</InnerPage>
		);
	}

	return (
		<InnerPage title={t("notificationSettings.title")} noPadding>
			<Container size={980} px="md" pt="md" pb={32}>
				<Text size="sm" c="dimmed" ta="center" mb="md">
					{t("notificationSettings.subtitle")}
				</Text>

				<Stack gap="md">
					{/* ── Pause Toggle ── */}
					<SettingCard
						icon={paused ? IconBellOff : IconBell}
						iconColor={paused ? "#fa5252" : "#40c057"}
						iconBg={paused ? "#fff5f5" : "#ebfbee"}
						title={t("notificationSettings.pause")}
						description={t("notificationSettings.pauseDesc")}
					>
						<Switch
							checked={paused}
							onChange={(e) => handlePausedChange(e.currentTarget.checked)}
							color="red"
							size="md"
							styles={{ track: { cursor: "pointer" } }}
							label={
								<Text size="sm" fw={600} c={paused ? "red.6" : "dimmed"}>
									{paused ? t("notificationSettings.statusPaused") : t("notificationSettings.statusActive")}
								</Text>
							}
						/>
					</SettingCard>

					{/* ── Daily Limit ── */}
					<SettingCard
						icon={IconGauge}
						iconColor="#228be6"
						iconBg="#e7f5ff"
						title={t("notificationSettings.dailyLimit")}
						description={t("notificationSettings.dailyLimitDesc")}
					>
						<Group justify="center" mb={12}>
							<Box
								style={{
									backgroundColor: "#e7f5ff",
									borderRadius: 10,
									padding: "6px 16px",
								}}
							>
								<Text size="sm" fw={700} c="blue.7">
									{t("notificationSettings.dailyLimitValue", {
										count: dailyLimit,
									})}
								</Text>
							</Box>
						</Group>
						<Box px={8}>
							<Slider
								color="blue"
								min={1}
								max={50}
								step={1}
								value={dailyLimit}
								onChange={handleDailyLimitChange}
								marks={[
									{ value: 1, label: "1" },
									{ value: 10, label: "10" },
									{ value: 25, label: "25" },
									{ value: 50, label: "50" },
								]}
								labelAlwaysOn={false}
								mb={24}
								disabled={paused}
							/>
						</Box>
					</SettingCard>

					{/* ── Time Windows ── */}
					<SettingCard
						icon={IconClock}
						iconColor="#be4bdb"
						iconBg="#f3f0ff"
						title={t("notificationSettings.timeWindows")}
						description={t("notificationSettings.timeWindowsDesc")}
					>
						<Stack gap={10}>
							{TIME_WINDOWS.map(({ value, labelKey }) => {
								const isActive = timeWindows.includes(value);
								return (
									<Box
										key={value}
										onClick={() => !paused && toggleWindow(value)}
										style={{
											display: "flex",
											alignItems: "center",
											justifyContent: "space-between",
											padding: "10px 14px",
											borderRadius: radii.md,
											backgroundColor: isActive ? "#f3f0ff" : "#f8f9fa",
											border: isActive
												? "1.5px solid #be4bdb"
												: "1.5px solid #e9ecef",
											cursor: paused ? "default" : "pointer",
											transition: "all 0.18s ease",
											opacity: paused ? 0.5 : 1,
										}}
									>
										<Text
											size="sm"
											fw={isActive ? 600 : 400}
											c={isActive ? "violet.7" : "gray.7"}
										>
											{t(labelKey)}
										</Text>
										<Switch
											checked={isActive}
											onChange={() => !paused && toggleWindow(value)}
											color="violet"
											size="sm"
											disabled={paused}
											onClick={(e) => e.stopPropagation()}
										/>
									</Box>
								);
							})}
						</Stack>
					</SettingCard>

					{/* ── Sources ── */}
					<SettingCard
						icon={IconFilter}
						iconColor="#ff922b"
						iconBg="#fff4e6"
						title={t("notificationSettings.sources")}
						description={t("notificationSettings.sourcesDesc")}
					>
						<Stack gap={10}>
							{(Object.keys(sources) as Array<keyof typeof sources>).map(
								(key) => (
									<Box
										key={key}
										onClick={() => !paused && toggleSource(key)}
										style={{
											display: "flex",
											alignItems: "center",
											justifyContent: "space-between",
											padding: "10px 14px",
											borderRadius: radii.md,
											backgroundColor: sources[key] ? "#fff4e6" : "#f8f9fa",
											border: sources[key]
												? "1.5px solid #ff922b"
												: "1.5px solid #e9ecef",
											cursor: paused ? "default" : "pointer",
											transition: "all 0.18s ease",
											opacity: paused ? 0.5 : 1,
										}}
									>
										<Text
											size="sm"
											fw={sources[key] ? 600 : 400}
											c={sources[key] ? "orange.7" : "gray.7"}
										>
											{t(`notificationSettings.source.${key}`)}
										</Text>
										<Checkbox
											checked={sources[key]}
											onChange={() => !paused && toggleSource(key)}
											color="orange"
											radius="sm"
											disabled={paused}
											onClick={(e) => e.stopPropagation()}
										/>
									</Box>
								),
							)}
						</Stack>
					</SettingCard>
				</Stack>
			</Container>
		</InnerPage>
	);
}

export const NotificationSettings = {
	route: "/notification-settings",
	Page,
};
