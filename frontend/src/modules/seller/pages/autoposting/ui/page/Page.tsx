import { useEffect, useState } from "react";
import {
	Alert,
	Badge,
	Box,
	Button,
	Card,
	Group,
	Stack,
	Text,
	TextInput,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
	IconBrandTelegram,
	IconCheck,
	IconRefresh,
	IconAlertTriangle,
} from "@tabler/icons-react";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { InnerPage } from "@shared/ui/InnerPage";
import { shadows, radii } from "@app/styles/theme";
import {
	$autopostStatus,
	$autopostPosts,
	$isLoadingAutopost,
	$isConnecting,
	$connectError,
} from "../../model/stores";
import {
	fetchAutopostStatusFx,
	fetchAutopostPostsFx,
	connectChannelFx,
	disconnectChannelFx,
	updateChannelPostFx,
	recreateChannelPostFx,
} from "../../model/effects";
import { MediaCutoffModal } from "@modules/seller/feature/media-cutoff-modal";

/**
 * Block D D4 — seller cabinet "Autoposting" page.
 *
 * Three states drive UX:
 *   1. Not connected → "Connect channel" form.
 *   2. Connection broken (verified_at=null while channel set) → reconnect prompt.
 *   3. Connected → channel info, stale-post counter, history list.
 *
 * 48h media-edit cutoff: API responds ``media_too_old`` to update calls;
 * we surface a 3-option modal (text-only / repost / cancel).
 */
function Page() {
	const { t } = useTranslation("seller");
	const navigate = useNavigate();
	const [status, posts, isLoading, isConnecting, connectError] = useUnit([
		$autopostStatus,
		$autopostPosts,
		$isLoadingAutopost,
		$isConnecting,
		$connectError,
	]);

	const [channelInput, setChannelInput] = useState("");
	const [
		mediaModalOpen,
		{ open: openMediaModal, close: closeMediaModal },
	] = useDisclosure(false);
	const [pendingPostId, setPendingPostId] = useState<string | null>(null);
	const [pendingPostAgeHours, setPendingPostAgeHours] = useState<number | null>(
		null,
	);

	useEffect(() => {
		void fetchAutopostStatusFx();
		void fetchAutopostPostsFx({ page: 1, pageSize: 20 });
	}, []);

	const handleConnect = async () => {
		const value = channelInput.trim();
		if (!value) return;
		const result = await connectChannelFx(value);
		if (result.status === "verified") {
			setChannelInput("");
			// $autopostStatus is the shared fetch-only store now — refresh it so
			// the UI flips to "connected" instead of relying on optimistic updates.
			void fetchAutopostStatusFx();
			void fetchAutopostPostsFx({ page: 1, pageSize: 20 });
		}
	};

	const handleDisconnect = async () => {
		await disconnectChannelFx();
		// Refresh the shared status store after the server confirms the drop.
		void fetchAutopostStatusFx();
	};

	const handleUpdatePost = async (postId: string, forceTextOnly = false) => {
		const res = await updateChannelPostFx({ postId, forceTextOnly });
		if (res.result === "media_too_old") {
			setPendingPostId(postId);
			setPendingPostAgeHours(res.post_age_hours ?? null);
			openMediaModal();
			return;
		}
		if (res.result === "queued") {
			// Refresh the post list — staleness flag is server-computed.
			void fetchAutopostPostsFx({ page: 1, pageSize: 20 });
		}
	};

	const handleMediaModalChoice = async (
		choice: "text_only" | "recreate" | "cancel",
	) => {
		const id = pendingPostId;
		closeMediaModal();
		setPendingPostId(null);
		setPendingPostAgeHours(null);
		if (!id || choice === "cancel") return;
		if (choice === "text_only") {
			await updateChannelPostFx({ postId: id, forceTextOnly: true });
		} else {
			// "recreate" = delete the old post + republish via the
			// dedicated /recreate endpoint. Loses accumulated views;
			// seller has already been warned in the modal copy.
			await recreateChannelPostFx(id);
		}
		void fetchAutopostPostsFx({ page: 1, pageSize: 20 });
	};

	// ────────────────────────────────────────────────────────────────
	const connected = status?.connected ?? false;
	const channelLabel = status?.channel_username
		? `@${status.channel_username}`
		: status?.channel_id
			? `id ${status.channel_id}`
			: "";
	const verificationLost =
		status &&
		!status.connected &&
		(status.channel_username || status.channel_id);

	return (
		<InnerPage title={t("autopost.title", "Autoposting")} noPadding>
			<Box p="md">
				<Stack gap="md">
					{!connected && !verificationLost && (
						<>
							{/* Block D D4 — explainer: why connect a channel (option B). */}
							<Card radius={radii.md} p="md" style={{ boxShadow: shadows.md }}>
								<Stack gap="sm">
									<Group gap="sm">
										<IconBrandTelegram size={20} color="#229ED9" />
										<Text fw={700}>
											{t(
												"autopost.explainer_title",
												"Autoposting to your Telegram channel",
											)}
										</Text>
									</Group>
									<Text size="sm" c="dimmed" lh={1.5}>
										{t(
											"autopost.explainer_body",
											"Your listings are published to your channel automatically, refreshed when you edit them, and marked SOLD when sold. More reach — more clients.",
										)}
									</Text>
									<Badge
										color="blue"
										variant="light"
										radius="sm"
										style={{ alignSelf: "flex-start" }}
									>
										{t("autopost.tariff_note", "Included in the realtor plan")}
									</Badge>
								</Stack>
							</Card>

							{status?.subscription_active === false ? (
								/* Block D D4 — tariff upsell (option C). In the test period
								   the backend reports subscription_active=true, so this
								   collapses to the connect form below. */
								<Button
									fullWidth
									size="md"
									onClick={() => navigate("/seller/tariffs")}
								>
									{t("autopost.upsell_cta", "Get the realtor plan")}
								</Button>
							) : (
								<Card radius={radii.md} p="md" style={{ boxShadow: shadows.md }}>
									<Stack gap="sm">
										<Text fw={700}>
											{t(
												"autopost.connect_title",
												"Connect your Telegram channel",
											)}
										</Text>
										<Text size="sm" c="dimmed">
											{t(
												"autopost.connect_help",
												"Add @ucharmarket_bot as administrator with post permission in your channel, then enter the channel username below.",
											)}
										</Text>
										<TextInput
											placeholder="@my_realestate_channel"
											value={channelInput}
											onChange={(e) => setChannelInput(e.currentTarget.value)}
										/>
										{connectError && (
											<Alert color="red" icon={<IconAlertTriangle size={16} />}>
												{t(
													`autopost.error.${connectError}`,
													t(
														"autopost.error.generic",
														"Could not verify channel",
													),
												)}
											</Alert>
										)}
										<Button
											onClick={handleConnect}
											loading={isConnecting}
											disabled={!channelInput.trim()}
										>
											{t("autopost.connect_btn", "Verify and connect")}
										</Button>
									</Stack>
								</Card>
							)}
						</>
					)}

					{verificationLost && (
						<Alert color="orange" icon={<IconAlertTriangle size={16} />}>
							<Stack gap="xs">
								<Text fw={600}>
									{t("autopost.reconnect_required", "Reconnect required")}
								</Text>
								<Text size="sm">
									{t(
										"autopost.reconnect_help",
										"The bot can no longer post to your channel. Please re-verify the connection.",
									)}
								</Text>
								<Button
									size="xs"
									onClick={() =>
										handleConnect()
									}
									disabled={!channelInput.trim() && !status?.channel_username}
									loading={isConnecting}
								>
									{t("autopost.reconnect_btn", "Reconnect")}
								</Button>
							</Stack>
						</Alert>
					)}

					{connected && (
						<Card radius={radii.md} p="md" style={{ boxShadow: shadows.md }}>
							<Stack gap="sm">
								<Group justify="space-between">
									<Group gap="sm">
										<IconCheck size={18} color="green" />
										<Text fw={700}>{channelLabel}</Text>
									</Group>
									<Button
										size="xs"
										color="red"
										variant="subtle"
										onClick={handleDisconnect}
									>
										{t("autopost.disconnect", "Disconnect")}
									</Button>
								</Group>
								{(status?.stale_count ?? 0) > 0 && (
									<Badge color="orange" variant="light">
										{t("autopost.stale_count", {
											count: status?.stale_count ?? 0,
											defaultValue: "{{count}} stale post(s)",
										})}
									</Badge>
								)}
							</Stack>
						</Card>
					)}

					{/* History list */}
					<Stack gap="xs">
						<Text fw={600} size="sm">
							{t("autopost.history_title", "Post history")}
						</Text>
						{(posts?.items ?? []).length === 0 && !isLoading && (
							<Text size="sm" c="dimmed">
								{t("autopost.history_empty", "No posts yet.")}
							</Text>
						)}
						{(posts?.items ?? []).map((post) => (
							<Card
								key={post.id}
								radius={radii.sm}
								p="sm"
								style={{ boxShadow: shadows.sm, border: "1px solid #f1f5f9" }}
							>
								<Group justify="space-between" wrap="nowrap">
									<Stack gap={2}>
										<Text size="sm" fw={500} lineClamp={1}>
											{post.listing_title ?? post.listing_id.slice(0, 8)}
										</Text>
										<Group gap={6}>
											<Text size="xs" c="dimmed">
												{new Date(post.posted_at).toLocaleDateString()}
											</Text>
											{post.is_stale && (
												<Badge size="xs" color="orange" variant="light">
													{t("autopost.badge_stale", "Stale")}
												</Badge>
											)}
											{post.status === "sold_marker" && (
												<Badge size="xs" color="red" variant="light">
													{t("autopost.badge_sold", "Sold")}
												</Badge>
											)}
											{post.status === "deleted" && (
												<Badge size="xs" color="gray" variant="light">
													{t("autopost.badge_deleted", "Deleted")}
												</Badge>
											)}
										</Group>
									</Stack>
									{post.status === "live" && (
										<Button
											size="xs"
											variant="light"
											leftSection={<IconRefresh size={14} />}
											onClick={() => handleUpdatePost(post.id)}
										>
											{t("autopost.update_btn", "Update")}
										</Button>
									)}
								</Group>
							</Card>
						))}
					</Stack>
				</Stack>
			</Box>

			{/* 48h media-edit cutoff modal (shared with "My listings"). */}
			<MediaCutoffModal
				opened={mediaModalOpen}
				postAgeHours={pendingPostAgeHours}
				onTextOnly={() => handleMediaModalChoice("text_only")}
				onRecreate={() => handleMediaModalChoice("recreate")}
				onCancel={() => handleMediaModalChoice("cancel")}
			/>
		</InnerPage>
	);
}

export const SellerAutoposting = {
	route: "/seller/autoposting",
	Page,
};
