import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Box, Text } from "@mantine/core";
import { IconBuilding } from "@tabler/icons-react";
import { useAuth } from "@app/providers/useAuth";
import { BuyerPhoneLogin } from "@shared/ui/BuyerPhoneLogin";
import { GradientHeader } from "@shared/ui/GradientHeader";

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
		<Box mih="100vh" bg="#f8f9fa">
			<GradientHeader
				icon={IconBuilding}
				title="UcharMarket"
				subtitle={t("auth.subtitle")}
				onBack={() => navigate(-1)}
			/>

			{/* Login form */}
			<Box px="md" style={{ marginTop: -36, position: "relative", zIndex: 1 }}>
				<BuyerPhoneLogin
					message={t("auth.loginMessage")}
					onCancel={() => navigate(-1)}
				/>
			</Box>

			{/* Terms footer */}
			<Box px="md" mt="lg">
				<Text ta="center" size="xs" c="dimmed" style={{ lineHeight: 1.5 }}>
					{t("auth.terms")}
				</Text>
			</Box>
		</Box>
	);
}
