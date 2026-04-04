import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ActionIcon, Box, Text } from "@mantine/core";
import { IconArrowLeft, IconBuilding } from "@tabler/icons-react";
import { useAuth } from "@app/providers/useAuth";
import { BuyerPhoneLogin } from "@shared/ui/BuyerPhoneLogin";

export function AuthPage() {
	const { t } = useTranslation("buyer");
	const { isAuthenticated } = useAuth();
	const navigate = useNavigate();

	// Redirect to profile once logged in
	useEffect(() => {
		if (isAuthenticated) {
			navigate(-1);
		}
	}, [isAuthenticated, navigate]);

	return (
		<Box
			style={{
				minHeight: "100dvh",
				backgroundColor: "#f8f9fa",
				display: "flex",
				flexDirection: "column",
				overflow: "auto",
			}}
		>
			{/* Compact gradient header */}
			<Box
				style={{
					background:
						"linear-gradient(135deg, #1971c2 0%, #40A7E3 50%, #74c0fc 100%)",
					padding: "24px 20px 40px",
					textAlign: "center",
					position: "relative",
					flexShrink: 0,
				}}
			>
				<ActionIcon
					variant="transparent"
					c="white"
					size={36}
					radius="xl"
					onClick={() => navigate(-1)}
					style={{ position: "absolute", top: 8, left: 12, zIndex: 2 }}
				>
					<IconArrowLeft size={22} />
				</ActionIcon>

				<Box
					style={{
						width: 56,
						height: 56,
						borderRadius: "50%",
						backgroundColor: "rgba(255,255,255,0.15)",
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						margin: "0 auto 10px",
					}}
				>
					<IconBuilding size={28} color="white" stroke={1.5} />
				</Box>
				<Text size="lg" fw={700} c="white">
					UcharMarket
				</Text>
				<Text size="xs" c="rgba(255,255,255,0.8)" mt={2}>
					{t("auth.subtitle")}
				</Text>
			</Box>

			{/* Login form */}
			<Box
				px="md"
				style={{ marginTop: -24, position: "relative", zIndex: 1, flex: 1 }}
			>
				<BuyerPhoneLogin
					message={t("auth.loginMessage")}
					onCancel={() => navigate(-1)}
				/>

				{/* Terms footer */}
				<Text
					ta="center"
					size="xs"
					c="dimmed"
					mt="md"
					style={{ lineHeight: 1.5 }}
				>
					{t("auth.terms")}
				</Text>
			</Box>
		</Box>
	);
}
