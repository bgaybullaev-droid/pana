import { useTranslation } from "react-i18next";
import { Box, Text } from "@mantine/core";
import {
	IconMessage2,
	IconSparkles,
	IconHeart,
	IconBell,
	IconShieldCheck,
	IconDeviceMobile,
} from "@tabler/icons-react";
import { InnerPage } from "@shared/ui/InnerPage";

const FEATURES_ICONS = [
	IconMessage2,
	IconSparkles,
	IconHeart,
	IconBell,
	IconShieldCheck,
	IconDeviceMobile,
];

function Page() {
	const { t } = useTranslation("buyer");

	return (
		<InnerPage title={t("settings.about")}>
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
						fontSize: 28,
						fontWeight: 700,
						color: "#1C1C1E",
						marginBottom: 4,
					}}
				>
					UcharMarket
				</Text>
				<Text
					style={{
						fontSize: 15,
						color: "#8E8E93",
						marginBottom: 16,
					}}
				>
					{t("about.tagline")}
				</Text>
				<Text
					style={{
						fontSize: 15,
						color: "#3C3C43",
						lineHeight: 1.6,
					}}
				>
					{t("about.description")}
				</Text>
			</Box>

			{/* Features */}
			<Box
				style={{
					backgroundColor: "#FFFFFF",
					borderRadius: 14,
					padding: 20,
				}}
			>
				<Text
					style={{
						fontSize: 16,
						fontWeight: 600,
						color: "#1C1C1E",
						marginBottom: 16,
					}}
				>
					{t("about.featuresTitle")}
				</Text>

				{FEATURES_ICONS.map((Icon, i) => (
					<Box
						key={i}
						style={{
							display: "flex",
							alignItems: "flex-start",
							gap: 12,
							marginBottom: i < 5 ? 16 : 0,
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
							{t(`about.feature${i + 1}`)}
						</Text>
					</Box>
				))}
			</Box>
		</InnerPage>
	);
}

export const About = {
	route: "/about",
	Page,
};
