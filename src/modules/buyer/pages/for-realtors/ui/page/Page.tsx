import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Box, Text, Button } from "@mantine/core";
import {
	IconChartBar,
	IconEye,
	IconUsers,
	IconRocket,
} from "@tabler/icons-react";
import { SubPageLayout } from "@shared/ui/SubPageLayout";

const BENEFITS_KEYS = [
	{ icon: IconRocket, key: "realtors.benefit1" },
	{ icon: IconEye, key: "realtors.benefit2" },
	{ icon: IconUsers, key: "realtors.benefit3" },
	{ icon: IconChartBar, key: "realtors.benefit4" },
];

function Page() {
	const { t } = useTranslation("buyer");
	const navigate = useNavigate();

	return (
		<SubPageLayout title={t("settings.forRealtors")}>
			{/* Hero */}
			<Box
				style={{
					backgroundColor: "#FFFFFF",
					borderRadius: 14,
					padding: 24,
					textAlign: "center",
					marginBottom: 16,
				}}
			>
				<Text
					style={{
						fontSize: 22,
						fontWeight: 700,
						color: "#1C1C1E",
						marginBottom: 8,
					}}
				>
					{t("realtors.title")}
				</Text>
				<Text
					style={{
						fontSize: 15,
						color: "#8E8E93",
						lineHeight: 1.6,
					}}
				>
					{t("realtors.description")}
				</Text>
			</Box>

			{/* Benefits */}
			<Box
				style={{
					backgroundColor: "#FFFFFF",
					borderRadius: 14,
					padding: 20,
					marginBottom: 16,
				}}
			>
				{BENEFITS_KEYS.map(({ icon: Icon, key }, i) => (
					<Box
						key={key}
						style={{
							display: "flex",
							alignItems: "flex-start",
							gap: 12,
							marginBottom: i < BENEFITS_KEYS.length - 1 ? 16 : 0,
						}}
					>
						<Box
							style={{
								width: 36,
								height: 36,
								borderRadius: 10,
								backgroundColor: "#E8F0FE",
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								flexShrink: 0,
							}}
						>
							<Icon size={18} color="#1A73E8" stroke={1.5} />
						</Box>
						<Text
							style={{
								fontSize: 14,
								color: "#3C3C43",
								lineHeight: 1.5,
								paddingTop: 8,
							}}
						>
							{t(key)}
						</Text>
					</Box>
				))}
			</Box>

			{/* CTA */}
			<Button
				fullWidth
				radius={14}
				size="lg"
				onClick={() => navigate("/become-seller")}
				styles={{
					root: {
						backgroundColor: "#1A73E8",
						height: 50,
						fontSize: 16,
						fontWeight: 600,
					},
				}}
			>
				{t("realtors.cta")}
			</Button>
		</SubPageLayout>
	);
}

export const ForRealtors = {
	route: "/for-realtors",
	Page,
};
