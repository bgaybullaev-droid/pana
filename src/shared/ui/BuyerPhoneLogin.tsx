import { useState, useEffect } from "react";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import { Box, Stack, Text, TextInput, Button, PinInput } from "@mantine/core";
import { IconPhone } from "@tabler/icons-react";
import { gradients, shadows } from "@app/styles/theme";
import {
	requestSellerOTP,
	verifySellerOTP,
	resetSellerOTPStep,
	$authError,
	$sellerOTPStep,
	$sellerOTPPhone,
	$isSellerOTPLoading,
	$sellerOTPDevCode,
} from "@shared/state/auth/model";

interface BuyerPhoneLoginProps {
	message?: string;
	onCancel?: () => void;
}

export function BuyerPhoneLogin({ message, onCancel }: BuyerPhoneLoginProps) {
	const { t } = useTranslation("buyer");
	const [phone, setPhone] = useState("");
	const [otpStep, otpPhone, isLoading, authError, devCode] = useUnit([
		$sellerOTPStep,
		$sellerOTPPhone,
		$isSellerOTPLoading,
		$authError,
		$sellerOTPDevCode,
	]);

	// Cleanup OTP state on unmount
	useEffect(() => {
		return () => {
			resetSellerOTPStep();
		};
	}, []);

	const digits = phone.replace(/\D/g, "");
	const isPhoneValid = digits.length === 9;

	const handleRequestOTP = () => {
		if (!isPhoneValid) return;
		requestSellerOTP(digits);
	};

	const handleVerifyOTP = (code: string) => {
		if (!otpPhone || code.length !== 6) return;
		const otpDigits = otpPhone.replace(/\D/g, "").slice(-9);
		verifySellerOTP({ phone: `+998${otpDigits}`, otp_code: code });
	};

	const maskedPhone = otpPhone
		? `+998 ${otpPhone.slice(-9, -7)} *** ** ${otpPhone.slice(-2)}`
		: "";

	return (
		<Box
			style={{
				backgroundColor: "white",
				borderRadius: 20,
				padding: 24,
				boxShadow: shadows.card,
			}}
		>
			{otpStep === "phone" ? (
				<Stack gap="md">
					{/* Header icon */}
					<Box style={{ textAlign: "center" }}>
						<Box
							style={{
								width: 56,
								height: 56,
								borderRadius: 16,
								background:
									"linear-gradient(135deg, rgba(34,139,230,0.1), rgba(64,167,227,0.15))",
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								margin: "0 auto 8px",
							}}
						>
							<IconPhone size={26} color="#228be6" stroke={1.8} />
						</Box>
						<Text size="sm" c="dimmed" ta="center">
							{message || t("auth.enterData")}
						</Text>
					</Box>

					{/* Phone field */}
					<TextInput
						placeholder={t("auth.phonePlaceholder")}
						type="tel"
						inputMode="numeric"
						autoComplete="tel"
						maxLength={9}
						leftSection={
							<Text
								size="sm"
								fw={600}
								c="dark.5"
								style={{ whiteSpace: "nowrap" }}
							>
								+998
							</Text>
						}
						leftSectionWidth={56}
						value={phone}
						onChange={(e) => {
							const val = e.currentTarget.value.replace(/\D/g, "");
							setPhone(val);
						}}
						error={authError}
						onKeyDown={(e) => {
							if (e.key === "Enter") handleRequestOTP();
						}}
						onPaste={(e) => {
							e.preventDefault();
							const pasted = e.clipboardData.getData("text").replace(/\D/g, "");
							setPhone(pasted.slice(0, 9));
						}}
						disabled={isLoading}
						radius={12}
						styles={{
							input: {
								backgroundColor: "#f8f9fa",
								border: "1.5px solid #e9ecef",
								height: 48,
								fontSize: 16,
								"&:focus": {
									backgroundColor: "#fff",
									borderColor: "#40A7E3",
									boxShadow: "0 0 0 3px rgba(64, 167, 227, 0.1)",
								},
							},
						}}
					/>

					{/* Submit button */}
					<Button
						onClick={handleRequestOTP}
						loading={isLoading}
						disabled={!isPhoneValid}
						fullWidth
						size="lg"
						radius={12}
						style={{
							background: isPhoneValid ? gradients.primary : undefined,
							boxShadow: isPhoneValid ? shadows.button : "none",
							height: 48,
							fontSize: 15,
							fontWeight: 700,
						}}
					>
						{t("common.login")}
					</Button>

					{onCancel && (
						<Button
							variant="subtle"
							color="gray"
							fullWidth
							size="md"
							radius={12}
							onClick={onCancel}
							disabled={isLoading}
						>
							{t("common.cancel")}
						</Button>
					)}
				</Stack>
			) : (
				<Stack gap="md" align="center">
					{/* OTP step */}
					<Box style={{ textAlign: "center" }}>
						<Box
							style={{
								width: 56,
								height: 56,
								borderRadius: 16,
								background:
									"linear-gradient(135deg, rgba(34,139,230,0.1), rgba(64,167,227,0.15))",
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								margin: "0 auto 8px",
							}}
						>
							<IconPhone size={26} color="#228be6" stroke={1.8} />
						</Box>
						<Text size="sm" fw={600} ta="center">
							{maskedPhone}
						</Text>
						<Text size="xs" c="dimmed" ta="center" mt={4}>
							{t("auth.enterOTP")}
						</Text>
					</Box>

					<PinInput
						length={6}
						size="md"
						type="number"
						onComplete={handleVerifyOTP}
						error={!!authError}
						disabled={isLoading}
						autoFocus
						styles={{
							root: { justifyContent: "center", gap: 8 },
							input: {
								width: 42,
								height: 42,
								borderRadius: 12,
								fontSize: 18,
								fontWeight: 600,
							},
						}}
					/>

					{authError && (
						<Text size="xs" c="red" ta="center">
							{authError}
						</Text>
					)}

					{/* Dev OTP code */}
					{devCode && (
						<Text size="xs" c="dimmed" ta="center">
							DEV: {devCode}
						</Text>
					)}

					<Button
						variant="subtle"
						color="blue"
						size="sm"
						onClick={() => resetSellerOTPStep()}
						disabled={isLoading}
					>
						{t("auth.changeNumber")}
					</Button>

					{onCancel && (
						<Button
							variant="subtle"
							color="gray"
							size="sm"
							onClick={onCancel}
							disabled={isLoading}
						>
							{t("common.cancel")}
						</Button>
					)}
				</Stack>
			)}
		</Box>
	);
}
