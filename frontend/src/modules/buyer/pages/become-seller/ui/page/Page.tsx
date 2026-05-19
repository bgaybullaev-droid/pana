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
} from "@mantine/core";
import { PhoneInput } from "@shared/ui/PhoneInput";
import {
	IconBuildingStore,
	IconBrandTelegram,

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
import { gradients, shadows, radii } from "@app/styles/theme";
import { InnerPage } from "@shared/ui/InnerPage";

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
			setPhone(user.phone);
		}
	}, [user, phone]);

	const handleSubmit = () => {
		const digits = phone.replace(/\D/g, "");
		if (digits.length !== 12) {
			notifications.show({
				title: t("register.error"),
				message: t("register.phoneError"),
				color: "red",
			});
			return;
		}
		registerAsSeller({
			phone: phone,
			company_name: companyName.trim() || undefined,
		});
	};

	if (isAuthLoading || !user) {
		return <LoadingOverlay visible />;
	}

	return (
		<InnerPage title={t("auth.becomeSeller")} onBack={() => navigate("/profile")} noPadding>

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

				{/* Decorative circles */}
				<Box
					style={{
						position: "absolute",
						top: -20,
						right: -20,
						width: 100,
						height: 100,
						borderRadius: radii.full,
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
						borderRadius: radii.full,
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
										borderRadius: radii.md,
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
					<PhoneInput
						label={t("register.phoneLabel")}
						placeholder="+998 XX XXX XX XX"
						value={phone}
						onChange={setPhone}
						onKeyDown={(e) => {
							if (e.key === "Enter") handleSubmit();
						}}
						disabled={isRegistering}
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
							boxShadow: shadows.accentOrange,
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

					{/* C1 V2.0: pricing visibility for prospective sellers */}
					<Box ta="center" mt="xs">
						<Button
							variant="subtle"
							color="orange"
							radius="xl"
							size="sm"
							onClick={() => navigate("/seller/tariffs")}
						>
							{t("nav.tariffs", { ns: "seller" })}
						</Button>
					</Box>
				</Stack>
			</Box>
		</InnerPage>
	);
}

export const BecomeSeller = {
	route: "/become-seller",
	Page,
};
