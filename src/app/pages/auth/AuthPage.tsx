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

	const handleCancel = () => {
		// Use React Router's internal history state to reliably check if we can go back.
		// If idx > 0, we have history within the app. Otherwise, default to home page.
		if (window.history.state && window.history.state.idx > 0) {
			navigate(-1);
		} else {
			navigate("/", { replace: true });
		}
	};

	return (
		<Box
			className="mesh-gradient"
			style={{
				minHeight: "100dvh",
				display: "flex",
				flexDirection: "column",
				overflow: "hidden",
				position: "relative",
			}}
		>
			{/* Top Bar */}
			<Box
				px="md"
				py="sm"
				style={{
					display: "flex",
					alignItems: "center",
					justifyContent: "space-between",
					position: "relative",
					zIndex: 10,
				}}
			>
				<ActionIcon
					variant="subtle"
					color="gray"
					size={40}
					radius="xl"
					onClick={handleCancel}
				>
					<IconArrowLeft size={24} />
				</ActionIcon>
			</Box>

			{/* Main Content */}
			<Box
				px="xl"
				style={{
					flex: 1,
					display: "flex",
					flexDirection: "column",
					justifyContent: "center",
					marginTop: -40,
				}}
			>
				{/* Branding Area */}
				<Box
					mb={40}
					className="animate-fade-in"
					style={{ textAlign: "center" }}
				>
					<Box
						style={{
							width: 80,
							height: 80,
							borderRadius: 24,
							background: "white",
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							margin: "0 auto 20px",
							boxShadow: "0 12px 24px rgba(0,0,0,0.06)",
							border: "1px solid rgba(0,0,0,0.02)",
							animation: "float 6s ease-in-out infinite",
						}}
					>
						<IconBuilding size={40} color="#1971c2" stroke={1.5} />
					</Box>
					<Text 
						size="32px" 
						fw={900} 
						variant="gradient"
						gradient={{ from: "#1971c2", to: "#40A7E3", deg: 135 }}
						style={{ letterSpacing: "-0.5px" }}
					>
						UcharMarket
					</Text>
					<Text size="sm" c="dimmed" mt={4} fw={500} px="xl">
						{t("auth.subtitle")}
					</Text>
				</Box>

				{/* Login Card */}
				<Box style={{ maxWidth: 400, margin: "0 auto", width: "100%" }}>
					<BuyerPhoneLogin
						message={t("auth.loginMessage")}
						onCancel={handleCancel}
					/>
				</Box>

				{/* Footer info */}
				<Text
					ta="center"
					size="xs"
					c="dimmed"
					mt={32}
					style={{ lineHeight: 1.6, maxWidth: 280, margin: "32px auto 0" }}
				>
					{t("auth.terms")}
				</Text>
			</Box>
		</Box>
	);
}

