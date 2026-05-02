import { useState } from "react";
import { useUnit } from "effector-react";
import { Box, Button, Loader, Stack, Text } from "@mantine/core";
import { IconBrandTelegram, IconPhone, IconShieldCheck } from "@tabler/icons-react";
import { useTelegram } from "@app/providers/useTelegram";
import {
	authenticateWithTelegram,
	authenticateWithTelegramFx,
	$authError,
} from "@shared/state/auth/model";
import { getApiError } from "@shared/api/client";

/**
 * Blocking phone-consent screen rendered inside Telegram WebApp when the user
 * has no authenticated session and no phone on file. Drives the full flow:
 *
 *   1. Tap "Share phone number" → window.Telegram.WebApp.requestContact()
 *   2. User confirms in Telegram → bot receives Contact message → bot caches
 *      phone in Redis at contact_share:{telegram_id}
 *   3. We re-fire POST /auth/telegram. Backend sees the Redis entry, links it
 *      to the user, issues tokens. $user populates → AuthProvider unmounts
 *      this gate.
 *
 * No phone → no access. Cancel/decline stays on the gate with a retry button.
 */
export function PhoneGate() {
	const { webApp, initData, user: tgUser } = useTelegram();
	const [pending, authError] = useUnit([
		authenticateWithTelegramFx.pending,
		$authError,
	]);
	const [localError, setLocalError] = useState<string | null>(null);
	const [waitingForContact, setWaitingForContact] = useState(false);

	const handleShare = () => {
		setLocalError(null);

		if (!webApp || typeof webApp.requestContact !== "function") {
			setLocalError(
				"Please update Telegram to the latest version to continue.",
			);
			return;
		}

		setWaitingForContact(true);
		try {
			webApp.requestContact((result) => {
				// Normalize both callback shapes: boolean (older clients) and
				// { status: "sent" | "cancelled" } (newer clients).
				const sent =
					result === true ||
					(typeof result === "object" &&
						result !== null &&
						(result as { status?: string }).status === "sent");

				if (!sent) {
					setWaitingForContact(false);
					setLocalError(
						"Phone sharing is required. Tap the button to try again.",
					);
					return;
				}

				// The bot's F.contact handler needs a moment to process the
				// webhook and write the phone to Redis before we claim it.
				window.setTimeout(() => {
					if (initData) {
						authenticateWithTelegram(initData);
					}
					setWaitingForContact(false);
				}, 800);
			});
		} catch (err) {
			setWaitingForContact(false);
			setLocalError(getApiError(err).message);
		}
	};

	const isLoading = pending || waitingForContact;
	const displayError = localError || authError;

	return (
		<Box
			className="mesh-gradient"
			style={{
				minHeight: "100dvh",
				display: "flex",
				flexDirection: "column",
				justifyContent: "center",
				alignItems: "center",
				padding: "24px 20px",
			}}
		>
			<Stack
				gap="lg"
				align="center"
				style={{ maxWidth: 380, width: "100%" }}
			>
				<Box
					style={{
						width: 88,
						height: 88,
						borderRadius: 24,
						background: "linear-gradient(135deg,#228be6,#40A7E3)",
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						boxShadow: "0 12px 32px rgba(34,139,230,0.35)",
					}}
				>
					<IconPhone size={44} color="white" stroke={1.8} />
				</Box>

				<Stack gap={6} align="center">
					<Text size="xl" fw={800} ta="center">
						{tgUser?.first_name
							? `Welcome, ${tgUser.first_name}`
							: "Welcome"}
					</Text>
					<Text size="sm" c="dimmed" ta="center" lh={1.5}>
						To use this service, you must share your phone number.
					</Text>
				</Stack>

				<Button
					fullWidth
					size="lg"
					radius="xl"
					leftSection={
						isLoading ? (
							<Loader size="xs" color="white" />
						) : (
							<IconBrandTelegram size={18} />
						)
					}
					onClick={handleShare}
					disabled={isLoading}
					style={{
						background: "linear-gradient(135deg,#228be6,#40A7E3)",
						height: 56,
						fontSize: 16,
						fontWeight: 700,
						boxShadow: "0 8px 24px rgba(34,139,230,0.35)",
					}}
				>
					{isLoading ? "Connecting…" : "Share phone number"}
				</Button>

				{displayError && (
					<Text size="sm" c="red" ta="center" fw={500}>
						{displayError}
					</Text>
				)}

				<Box
					style={{
						display: "flex",
						alignItems: "center",
						gap: 8,
						marginTop: 4,
					}}
				>
					<IconShieldCheck size={16} color="#868e96" />
					<Text size="xs" c="dimmed">
						Your number is handled by Telegram — no SMS codes.
					</Text>
				</Box>
			</Stack>
		</Box>
	);
}
