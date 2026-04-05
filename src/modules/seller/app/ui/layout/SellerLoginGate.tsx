import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
	Box,
	Text,
	Button,
	Stack,
	PinInput,
	LoadingOverlay,
} from "@mantine/core";
import { PhoneInput } from "@shared/ui/PhoneInput";
import { IconBuildingStore } from "@tabler/icons-react";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import {
	requestSellerOTP,
	verifySellerOTP,
	resetSellerOTPStep,
	$authError,
	$sellerOTPStep,
	$sellerOTPPhone,
	$isSellerOTPLoading,
} from "@shared/state/auth/model";
import { LanguageSwitcher } from "@shared/ui/LanguageSwitcher";
import { shadows } from "@app/styles/theme";

const SELLER_BOT_USERNAME =
	import.meta.env.VITE_SELLER_BOT_USERNAME || "testourbor_bot";

export function SellerLoginGate() {
	const navigate = useNavigate();
	const { t } = useTranslation("seller");
	const [phone, setPhone] = useState("");
	const [otpStep, otpPhone, isLoading, authError] = useUnit([
		$sellerOTPStep,
		$sellerOTPPhone,
		$isSellerOTPLoading,
		$authError,
	]);

	const handleRequestOTP = () => {
		const digits = phone.replace(/\D/g, "");
		if (digits.length !== 12) return;
		requestSellerOTP(digits.slice(3));
	};

	const handleVerifyOTP = (code: string) => {
		if (!otpPhone || code.length !== 6) return;
		const digits = otpPhone.replace(/\D/g, "").slice(-9);
		verifySellerOTP({ phone: `+998${digits}`, otp_code: code });
	};

	const handleBack = () => {
		resetSellerOTPStep();
	};

	const maskedPhone = otpPhone
		? `+998 ${otpPhone.slice(-9, -7)} *** ** ${otpPhone.slice(-2)}`
		: "";

	return (
		<Box
			style={{
				display: "flex",
				flexDirection: "column",
				height: "100%",
				width: "100%",
			}}
		>
			{/* Gradient top section */}
			<Box
				style={{
					background: "linear-gradient(135deg, #228be6 0%, #40A7E3 100%)",
					padding: "48px 20px 80px",
					textAlign: "center",
					flexShrink: 0,
				}}
			>
				<Box
					style={{
						display: "flex",
						justifyContent: "flex-end",
						marginBottom: 16,
					}}
				>
					<LanguageSwitcher />
				</Box>
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
					{t("auth.sellerPanel")}
				</Text>
				<Text size="sm" c="rgba(255,255,255,0.8)" mt={4}>
					{otpStep === "phone"
						? t("auth.loginSubtitlePhone")
						: t("auth.loginSubtitleOTP")}
				</Text>
			</Box>

			{/* White card form section */}
			<Box
				style={{
					background: "white",
					borderRadius: "24px 24px 0 0",
					marginTop: -40,
					padding: "28px 20px",
					flex: 1,
					position: "relative",
				}}
			>
				<LoadingOverlay visible={isLoading} />

				{otpStep === "phone" ? (
					<Stack gap="md" align="center" maw={400} mx="auto">
						<PhoneInput
							w="100%"
							placeholder="+998 XX XXX XX XX"
							value={phone}
							onChange={setPhone}
							error={authError}
							onKeyDown={(e) => {
								if (e.key === "Enter") handleRequestOTP();
							}}
							disabled={isLoading}
						/>

						<Button
							onClick={handleRequestOTP}
							loading={isLoading}
							w="100%"
							size="lg"
							radius="xl"
							style={{
								background: "linear-gradient(135deg, #228be6, #40A7E3)",
								border: "none",
								boxShadow: shadows.accent,
							}}
						>
							{t("auth.getCode")}
						</Button>

						<Text size="sm" c="dimmed" ta="center">
							{t("auth.noAccount")}{" "}
							<Text
								component="a"
								href={`https://t.me/${SELLER_BOT_USERNAME}`}
								target="_blank"
								rel="noopener noreferrer"
								size="sm"
								c="blue.6"
								fw={500}
								style={{ textDecoration: "none" }}
							>
								{t("auth.registerViaBot")}
							</Text>
						</Text>

						<Button
							variant="subtle"
							color="gray"
							size="sm"
							onClick={() => navigate("/")}
						>
							{t("auth.goHome")}
						</Button>
					</Stack>
				) : (
					<Stack gap="md" align="center" maw={400} mx="auto">
						<Text size="sm" c="dimmed" ta="center">
							{t("auth.enterOTP")}
						</Text>
						<Text size="sm" fw={600} ta="center">
							{maskedPhone}
						</Text>

						<PinInput
							length={6}
							size="lg"
							type="number"
							onComplete={handleVerifyOTP}
							error={!!authError}
							disabled={isLoading}
							autoFocus
							style={{ justifyContent: "center" }}
						/>

						{authError && (
							<Text size="xs" c="red" ta="center">
								{authError}
							</Text>
						)}

						<Button
							variant="subtle"
							color="blue"
							size="sm"
							onClick={handleBack}
							disabled={isLoading}
						>
							{t("auth.changeNumber")}
						</Button>
					</Stack>
				)}
			</Box>
		</Box>
	);
}
