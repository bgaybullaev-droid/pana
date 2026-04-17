import { useState, useEffect } from "react";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import { Box, Stack, Text, Button, PinInput } from "@mantine/core";
import { PhoneInput } from "@shared/ui/PhoneInput";
import { IconPhone } from "@tabler/icons-react";
import { gradients } from "@app/styles/theme";
import {
	requestSellerOTP,
	verifySellerOTP,
	resetSellerOTPStep,
	$authError,
	$sellerOTPStep,
	$sellerOTPPhone,
	$isSellerOTPLoading,
	$sellerOTPDevCode,
	$sellerOTPExpiresAt,
} from "@shared/state/auth/model";

interface BuyerPhoneLoginProps {
	message?: string;
	onCancel?: () => void;
}

export function BuyerPhoneLogin({ message, onCancel }: BuyerPhoneLoginProps) {
	const { t } = useTranslation("buyer");
	const [phone, setPhone] = useState("");
	const [pin, setPin] = useState("");
	const [otpStep, otpPhone, isLoading, authError, devCode, expiresAt] = useUnit(
		[
			$sellerOTPStep,
			$sellerOTPPhone,
			$isSellerOTPLoading,
			$authError,
			$sellerOTPDevCode,
			$sellerOTPExpiresAt,
		],
	);

	const [timeLeft, setTimeLeft] = useState(0);

	// Timer effect
	useEffect(() => {
		if (!expiresAt) {
			setTimeLeft(0);
			return;
		}

		const interval = setInterval(() => {
			const remaining = Math.max(
				0,
				Math.floor((expiresAt - Date.now()) / 1000),
			);
			setTimeLeft(remaining);
			if (remaining === 0) {
				clearInterval(interval);
			}
		}, 1000);

		// Initial set
		setTimeLeft(Math.max(0, Math.floor((expiresAt - Date.now()) / 1000)));

		return () => clearInterval(interval);
	}, [expiresAt]);

	// Cleanup OTP state on unmount
	useEffect(() => {
		return () => {
			resetSellerOTPStep();
		};
	}, []);

	const digits = phone.replace(/\D/g, "");
	const isPhoneValid = digits.length === 12;

	const handleRequestOTP = () => {
		if (!isPhoneValid) return;
		requestSellerOTP(digits.slice(3));
	};

	const handleVerifyOTP = (code: string) => {
		if (!otpPhone || code.length !== 6) return;
		const otpDigits = otpPhone.replace(/\D/g, "").slice(-9);
		verifySellerOTP({ phone: `+998${otpDigits}`, otp_code: code });
	};

	const handlePaste = async () => {
		try {
			const text = await navigator.clipboard.readText();
			const cleanText = text.replace(/\D/g, "").slice(0, 6);
			if (cleanText.length === 6) {
				setPin(cleanText);
				handleVerifyOTP(cleanText);
			}
		} catch (err) {
			console.error("Failed to read clipboard:", err);
		}
	};

	const maskedPhone = otpPhone
		? `+998 ${otpPhone.slice(-9, -7)} *** ** ${otpPhone.slice(-2)}`
		: "";

	return (
		<Box
			className="glass animate-fade-in"
			style={{
				borderRadius: 28,
				padding: 28,
				boxShadow: "0 20px 40px rgba(0,0,0,0.08)",
				position: "relative",
				overflow: "hidden",
			}}
		>
			{otpStep === "phone" ? (
				<Stack gap="xl" style={{ position: "relative", zIndex: 1 }}>
					{/* Header icon */}
					<Box style={{ textAlign: "center" }}>
						<Box
							style={{
								width: 64,
								height: 64,
								borderRadius: 20,
								background: "linear-gradient(135deg, #228be6, #4dabf7)",
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								margin: "0 auto 16px",
								boxShadow: "0 8px 16px rgba(34,139,230,0.25)",
							}}
						>
							<IconPhone size={28} color="white" stroke={1.8} />
						</Box>
						<Text size="lg" fw={700} ta="center" mb={4}>
							{t("common.login")}
						</Text>
						<Text size="sm" c="dimmed" ta="center" px="md">
							{message || t("auth.enterData")}
						</Text>
					</Box>

					{/* Phone field */}
					<Box>
						<PhoneInput
							placeholder="+998 XX XXX XX XX"
							value={phone}
							onChange={setPhone}
							error={authError}
							onKeyDown={(e) => {
								if (e.key === "Enter") handleRequestOTP();
							}}
							disabled={isLoading}
						/>
					</Box>

					{/* Submit button */}
					<Stack gap="sm">
						<Button
							onClick={handleRequestOTP}
							loading={isLoading}
							disabled={!isPhoneValid}
							fullWidth
							size="lg"
							radius="xl"
							style={{
								background: isPhoneValid ? gradients.primary : "#e9ecef",
								color: isPhoneValid ? "white" : "#adb5bd",
								boxShadow: isPhoneValid
									? "0 8px 20px rgba(34,139,230,0.3)"
									: "none",
								height: 56,
								fontSize: 16,
								fontWeight: 700,
								transition: "all 0.3s ease",
							}}
						>
							{authError?.toLowerCase().includes("запросите") ||
							authError?.toLowerCase().includes("истёк")
								? "Запросить новый код"
								: t("common.login")}
						</Button>

						{onCancel && (
							<Button
								variant="subtle"
								color="gray"
								fullWidth
								size="md"
								radius="xl"
								onClick={onCancel}
								disabled={isLoading}
								style={{ height: 48 }}
							>
								{t("common.cancel")}
							</Button>
						)}
					</Stack>
				</Stack>
			) : (
				<Stack
					gap="xl"
					align="center"
					style={{ position: "relative", zIndex: 1 }}
				>
					{/* OTP step */}
					<Box style={{ textAlign: "center" }}>
						<Box
							style={{
								width: 64,
								height: 64,
								borderRadius: 20,
								background: "linear-gradient(135deg, #228be6, #4dabf7)",
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								margin: "0 auto 16px",
								boxShadow: "0 8px 16px rgba(34,139,230,0.25)",
							}}
						>
							<IconPhone size={28} color="white" stroke={1.8} />
						</Box>
						<Text size="lg" fw={700} ta="center" mb={4}>
							{t("auth.enterOTP")}
						</Text>
						<Text size="sm" fw={600} ta="center" c="blue">
							{maskedPhone}
						</Text>
					</Box>

					<PinInput
						length={6}
						size="lg"
						type="number"
						value={pin}
						onChange={setPin}
						onComplete={handleVerifyOTP}
						error={!!authError}
						disabled={isLoading}
						autoFocus
						styles={{
							root: { justifyContent: "center", gap: 10 },
							input: {
								width: 46,
								height: 54,
								borderRadius: 14,
								fontSize: 22,
								fontWeight: 700,
								backgroundColor: "rgba(0,0,0,0.03)",
								border: "1px solid rgba(0,0,0,0.05)",
								transition: "all 0.2s ease",
								"&:focus": {
									borderColor: "#228be6",
									backgroundColor: "white",
									boxShadow: "0 0 0 4px rgba(34,139,230,0.1)",
								},
							},
						}}
					/>

					{authError && (
						<Text size="sm" c="red" ta="center" fw={500}>
							{authError}
						</Text>
					)}

					{/* Dev OTP code */}
					{devCode && (
						<Box
							py={8}
							px={16}
							style={{
								backgroundColor: "rgba(34,139,230,0.05)",
								borderRadius: 12,
								width: "100%",
							}}
						>
							<Text size="xs" c="blue" ta="center" fw={600}>
								TEST CODE: {devCode}
							</Text>
						</Box>
					)}

					{/* Secondary Actions (Side-by-side) */}
					<Box style={{ display: "flex", gap: 8, width: "100%" }}>
						{timeLeft > 0 && (
							<Button
								variant="outline"
								color="gray"
								radius="xl"
								size="sm"
								style={{ flex: 1 }}
								styles={{
									label: { fontSize: 13 },
								}}
								onClick={handlePaste}
								disabled={isLoading}
							>
								{t("auth.pasteCode")}
							</Button>
						)}

						<Button
							variant="light"
							color="blue"
							radius="xl"
							size="sm"
							style={{ flex: 1 }}
							styles={{
								label: { fontSize: 13 },
							}}
							onClick={() => {
								setPin("");
								resetSellerOTPStep();
							}}
							disabled={isLoading}
						>
							{t("auth.changeNumber")}
						</Button>
					</Box>

					{/* Timer or Expiration info */}
					{timeLeft > 0 ? (
						<Text size="sm" c="dimmed" ta="center">
							{t("auth.resendCodeTimer", {
								time: `${Math.floor(timeLeft / 60)
									.toString()
									.padStart(
										2,
										"0",
									)}:${(timeLeft % 60).toString().padStart(2, "0")}`,
							})}
						</Text>
					) : (
						<Text size="sm" c="red" ta="center" fw={500}>
							Срок действия кода истёк
						</Text>
					)}

					{/* Main Action Button */}
					<Button
						fullWidth
						size="lg"
						radius="xl"
						onClick={
							timeLeft > 0 ? () => handleVerifyOTP(pin) : handleRequestOTP
						}
						disabled={isLoading || (timeLeft > 0 && pin.length !== 6)}
						loading={isLoading}
						style={{
							background:
								(timeLeft > 0 && pin.length === 6) || timeLeft === 0
									? gradients.primary
									: "#e9ecef",
							boxShadow:
								(timeLeft > 0 && pin.length === 6) || timeLeft === 0
									? "0 8px 20px rgba(34,139,230,0.3)"
									: undefined,
							color:
								(timeLeft > 0 && pin.length === 6) || timeLeft === 0
									? undefined
									: "#adb5bd",
							height: 56,
							fontSize: 16,
							fontWeight: 700,
							transition: "all 0.3s ease",
						}}
					>
						{timeLeft > 0 ? t("common.login") : "Запросить новый код"}
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
