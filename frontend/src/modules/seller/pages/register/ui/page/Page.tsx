import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useUnit } from "effector-react";
import {
	Container,
	Stack,
	Text,
	TextInput,
	Button,
	Box,
	LoadingOverlay,
} from "@mantine/core";
import { PhoneInput } from "@shared/ui/PhoneInput";
import { InnerPage } from "@shared/ui/InnerPage";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useEffectorNotification } from "@shared/hooks/useEffectorNotification";
import {
	IconUser,
	IconBuildingStore,
	IconList,
	IconChartBar,
	IconMessageCircle,
} from "@tabler/icons-react";
import {
	$sellerProfile,
	$isLoadingProfile,
	$sellerError,
	registerAsSeller,
	registerAsSellerFx,
	resetSellerState,
} from "@modules/seller/shared/state";
import { BenefitRow } from "../main/BenefitRow";
import { radii, shadows, spacing, surface } from "@app/styles/theme";

function Page() {
	const { t } = useTranslation("seller");
	const navigate = useNavigate();
	const [sellerProfile, isLoading, error] = useUnit([
		$sellerProfile,
		$isLoadingProfile,
		$sellerError,
	]);
	const redirectCheckedRef = useRef(false);

	const form = useForm({
		initialValues: {
			phone: "",
			company_name: "",
		},
		validate: {
			phone: (value: string) => {
				if (!value) return t("register.phoneRequired");
				// Uzbek phone format: +998 XX XXX XX XX
				const phoneRegex = /^\+998\d{9}$/;
				if (!phoneRegex.test(value.replace(/\s/g, ""))) {
					return t("register.phoneFormat");
				}
				return null;
			},
		},
	});

	// Handle successful registration
	useEffectorNotification(
		registerAsSellerFx,
		{
			title: t("register.welcomeTitle"),
			message: t("register.welcomeMessage"),
			color: "green",
		},
		() => navigate("/seller/dashboard"),
	);

	// Show error notification
	useEffect(() => {
		if (error) {
			notifications.show({
				title: t("notifications.error"),
				message: error,
				color: "red",
			});
			resetSellerState();
		}
	}, [error, t]);

	// Redirect if already registered
	useEffect(() => {
		if (redirectCheckedRef.current) return;
		if (sellerProfile) {
			redirectCheckedRef.current = true;
			navigate("/seller/dashboard");
		}
	}, [sellerProfile, navigate]);

	const handleSubmit = (values: typeof form.values) => {
		registerAsSeller({
			phone: values.phone.replace(/\s/g, ""),
			company_name: values.company_name || undefined,
		});
	};

	return (
		<InnerPage title={t("register.title")} noPadding>
			<LoadingOverlay visible={isLoading} />

			{/* Gradient Hero Section */}
			<Box
				style={{
					background:
						"linear-gradient(135deg, #228be6 0%, #40A7E3 50%, #74c0fc 100%)",
					padding: "48px 20px 80px",
					textAlign: "center",
					position: "relative",
					overflow: "hidden",
				}}
			>
				{/* Decorative circles */}
				<Box
					style={{
						position: "absolute",
						top: -30,
						right: -30,
						width: 120,
						height: 120,
						borderRadius: radii.full,
						backgroundColor: "rgba(255,255,255,0.08)",
					}}
				/>
				<Box
					style={{
						position: "absolute",
						bottom: 20,
						left: -20,
						width: 80,
						height: 80,
						borderRadius: radii.full,
						backgroundColor: "rgba(255,255,255,0.06)",
					}}
				/>

				<Box
					style={{
						width: 80,
						height: 80,
						borderRadius: 20,
						backgroundColor: "rgba(255,255,255,0.15)",
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						margin: "0 auto 16px",
					}}
				>
					<IconBuildingStore size={44} color="white" stroke={1.5} />
				</Box>

				<Text size="xl" fw={700} c="white">
					{t("register.title")}
				</Text>
				<Text size="sm" c="rgba(255,255,255,0.8)" mt={4}>
					{t("register.subtitle")}
				</Text>
			</Box>

			{/* Overlapping white container */}
			<Container
				size={980}
				px="md"
				style={{
					marginTop: -40,
					position: "relative",
					zIndex: 1,
					paddingBottom: 24,
				}}
			>
				<Stack gap="md">
					{/* Benefits Cards */}
					<Box
						style={{
							backgroundColor: surface.card,
							borderRadius: radii.lg,
							padding: spacing.card,
							boxShadow: shadows.md,
						}}
					>
						<Text size="xs" fw={600} c="blue.6" tt="uppercase" mb="sm" lh={1}>
							{t("register.benefits")}
						</Text>
						<Stack gap="sm">
							<BenefitRow
								icon={IconList}
								color="blue"
								title={t("register.benefitListingsTitle")}
								description={t("register.benefitListingsDesc")}
							/>
							<BenefitRow
								icon={IconChartBar}
								color="green"
								title={t("register.benefitAnalyticsTitle")}
								description={t("register.benefitAnalyticsDesc")}
							/>
							<BenefitRow
								icon={IconMessageCircle}
								color="orange"
								title={t("register.benefitLeadsTitle")}
								description={t("register.benefitLeadsDesc")}
							/>
						</Stack>
					</Box>

					{/* Registration Form */}
					<Box
						style={{
							backgroundColor: surface.card,
							borderRadius: radii.lg,
							padding: spacing.card,
							boxShadow: shadows.md,
						}}
					>
						<Text size="xs" fw={600} c="blue.6" tt="uppercase" mb="sm" lh={1}>
							{t("register.formTitle")}
						</Text>
						<form onSubmit={form.onSubmit(handleSubmit)}>
							<Stack gap="sm">
								<PhoneInput
									label={t("register.phone")}
									placeholder="+998 XX XXX XX XX"
									value={form.values.phone}
									onChange={(val) => form.setFieldValue("phone", val)}
									error={form.errors.phone as string | null | false}
								/>

								<TextInput
									label={t("register.companyName")}
									placeholder={t("register.companyPlaceholder")}
									autoComplete="organization"
									leftSection={<IconUser size={16} />}
									radius="md"
									{...form.getInputProps("company_name")}
								/>

								<Text size="xs" c="dimmed">
									{t("register.terms")}
								</Text>

								<Button
									type="submit"
									size="lg"
									fullWidth
									radius="xl"
									loading={isLoading}
									style={{
										background: "linear-gradient(135deg, #228be6, #40A7E3)",
										border: "none",
										boxShadow: shadows.accent,
									}}
								>
									{t("register.submit")}
								</Button>
							</Stack>
						</form>
					</Box>
				</Stack>
			</Container>
		</InnerPage>
	);
}

export const SellerRegister = {
	route: "/seller/register",
	Page,
};
