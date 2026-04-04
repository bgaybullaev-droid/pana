import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "@app/providers/useAuth";
import {
	Box,
	Text,
	Stack,
	TextInput,
	Button,
	LoadingOverlay,
	ActionIcon,
} from "@mantine/core";
import {
	IconBuildingStore,
	IconBrandTelegram,
	IconArrowLeft,
	IconCheck,
} from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import {
	registerAsSeller,
	registerAsSellerFx,
	$isLoadingProfile,
	$sellerError,
} from "@modules/seller/shared/state";
import { SELLER_BOT_USERNAME } from "@shared/lib/constants";
import { gradients } from "@app/styles/theme";

function Page() {
	const navigate = useNavigate();
	const { t } = useTranslation("seller");
	const { user, isLoading: isAuthLoading } = useAuth();
	const [phone, setPhone] = useState("");
	const [companyName, setCompanyName] = useState("");
	const [isRegistering, sellerError] = useUnit([
		$isLoadingProfile,
		$sellerError,
	]);
	const watcherRef = useRef(false);

	// Redirect: not logged in → /auth
	useEffect(() => {
		if (!isAuthLoading && !user) {
			navigate("/auth", { replace: true });
		}
	}, [isAuthLoading, user, navigate]);

	// Redirect: already a seller → /my-dashboard
	useEffect(() => {
		if (user?.is_seller) {
			navigate("/seller/dashboard", { replace: true });
		}
	}, [user, navigate]);

	// On successful registration → redirect to /create
	useEffect(() => {
		if (watcherRef.current) return;
		watcherRef.current = true;
		const unwatch = registerAsSellerFx.doneData.watch(() => {
			notifications.show({
				title: t("register.successTitle"),
				message: t("register.successMessage"),
				color: "green",
			});
			navigate("/seller/create", { replace: true });
		});
		return () => unwatch();
	}, [navigate, t]);

	// Pre-fill phone from user data if available
	useEffect(() => {
		if (user?.phone && !phone) {
			setPhone(user.phone.replace("+998", ""));
		}
	}, [user, phone]);

	const handleSubmit = () => {
		const digits = phone.replace(/\D/g, "");
		if (digits.length !== 9) {
			notifications.show({
				title: t("register.error"),
				message: t("register.phoneError"),
				color: "red",
			});
			return;
		}
		registerAsSeller({
			phone: `+998${digits}`,
			company_name: companyName.trim() || undefined,
		});
	};

	if (isAuthLoading || !user) {
		return <LoadingOverlay visible />;
	}

	return (
		<Box
			style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}
		>
			{/* Gradient header */}
			<Box
				style={{
					background: gradients.orange,
					padding: "48px 20px 80px",
					textAlign: "center",
					flexShrink: 0,
					position: "relative",
				}}
			>
				{/* Back button */}
				<ActionIcon
					variant="transparent"
					size={56}
					onClick={() => navigate("/profile")}
					style={{
						position: "absolute",
						top: 12,
						left: 12,
						zIndex: 2,
						backgroundColor: "rgba(255, 255, 255, 0.65)",
						backdropFilter: "blur(20px) saturate(180%)",
						WebkitBackdropFilter: "blur(20px) saturate(180%)",
						border: "1px solid rgba(255, 255, 255, 0.5)",
						boxShadow: "0 4px 20px rgba(0, 0, 0, 0.04)",
						borderRadius: "50%",
					}}
				>
					<IconArrowLeft size={24} color="#868e96" />
				</ActionIcon>

				{/* Decorative circles */}
				<Box
					style={{
						position: "absolute",
						top: -20,
						right: -20,
						width: 100,
						height: 100,
						borderRadius: "50%",
						backgroundColor: "rgba(255,255,255,0.08)",
					}}
				/>
				<Box
					style={{
						position: "absolute",
						bottom: -30,
						left: -10,
						width: 70,
						height: 70,
						borderRadius: "50%",
						backgroundColor: "rgba(255,255,255,0.06)",
					}}
				/>

				<Box
					style={{
						width: 72,
						height: 72,
						borderRadius: 18,
						backgroundColor: "rgba(255,255,255,0.2)",
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						margin: "0 auto 16px",
					}}
				>
					<IconBuildingStore size={36} color="white" stroke={1.5} />
				</Box>
				<Text size="xl" fw={700} c="white">
					{t("auth.becomeSeller")}
				</Text>
				<Text size="sm" c="rgba(255,255,255,0.8)" mt={4}>
					{t("register.subtitle")}
				</Text>
			</Box>

			{/* White card form */}
			<Box
				style={{
					background: "white",
					borderRadius: "24px 24px 0 0",
					marginTop: -40,
					padding: "32px 20px",
					flex: 1,
					position: "relative",
				}}
			>
				<LoadingOverlay visible={isRegistering} />

				<Stack gap="lg" maw={400} mx="auto">
					{/* Benefits */}
					<Stack gap="xs">
						{[
							t("register.benefit1"),
							t("register.benefit2"),
							t("register.benefit3"),
						].map((benefit, i) => (
							<Box
								key={i}
								style={{ display: "flex", alignItems: "center", gap: 8 }}
							>
								<Box
									style={{
										width: 24,
										height: 24,
										borderRadius: 12,
										backgroundColor: "#ebfbee",
										display: "flex",
										alignItems: "center",
										justifyContent: "center",
										flexShrink: 0,
									}}
								>
									<IconCheck size={14} color="#40c057" stroke={2.5} />
								</Box>
								<Text size="sm" c="gray.7">
									{benefit}
								</Text>
							</Box>
						))}
					</Stack>

					{/* Phone input */}
					<TextInput
						label={t("register.phoneLabel")}
						placeholder="00 000 00 00"
						radius="xl"
						size="md"
						type="tel"
						inputMode="numeric"
						autoComplete="tel"
						maxLength={9}
						leftSection={
							<Text size="sm" c="dimmed" fw={500}>
								+998
							</Text>
						}
						leftSectionWidth={56}
						value={phone}
						onChange={(e) => {
							const val = e.currentTarget.value.replace(/\D/g, "");
							setPhone(val);
						}}
						onKeyDown={(e) => {
							if (e.key === "Enter") handleSubmit();
						}}
						onPaste={(e) => {
							e.preventDefault();
							const pasted = e.clipboardData.getData("text").replace(/\D/g, "");
							setPhone(pasted.slice(0, 9));
						}}
						disabled={isRegistering}
						required
					/>

					{/* Company name (optional) */}
					<TextInput
						label={t("register.companyLabel")}
						placeholder={t("register.companyPlaceholder")}
						radius="xl"
						size="md"
						autoComplete="organization"
						value={companyName}
						onChange={(e) => setCompanyName(e.currentTarget.value)}
						disabled={isRegistering}
					/>

					{/* Error display */}
					{sellerError && (
						<Text size="sm" c="red" ta="center">
							{sellerError}
						</Text>
					)}

					{/* Submit button */}
					<Button
						onClick={handleSubmit}
						loading={isRegistering}
						size="lg"
						fullWidth
						radius="xl"
						style={{
							background: gradients.orange,
							border: "none",
							boxShadow: "0 4px 12px rgba(255,110,1,0.3)",
						}}
					>
						{t("register.submit")}
					</Button>

					{/* Telegram bot alternative */}
					<Box ta="center">
						<Text size="sm" c="dimmed" mb="xs">
							{t("register.orViaTelegram")}
						</Text>
						<Button
							component="a"
							href={`https://t.me/${SELLER_BOT_USERNAME}`}
							target="_blank"
							rel="noopener noreferrer"
							variant="light"
							color="blue"
							radius="xl"
							leftSection={<IconBrandTelegram size={18} />}
						>
							{t("auth.registerViaBot")}
						</Button>
					</Box>
				</Stack>
			</Box>
		</Box>
	);
}

export const BecomeSeller = {
	route: "/become-seller",
	Page,
};
