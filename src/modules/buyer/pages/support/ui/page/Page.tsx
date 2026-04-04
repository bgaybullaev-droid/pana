import { useTranslation } from "react-i18next";
import { Box, Text, UnstyledButton } from "@mantine/core";
import { IconBrandTelegram, IconPhone, IconMail } from "@tabler/icons-react";
import { SubPageLayout } from "@shared/ui/SubPageLayout";

function Page() {
	const { t } = useTranslation("buyer");

	const channels = [
		{
			icon: IconBrandTelegram,
			label: t("support.telegram"),
			subtitle: "@ucharmarket_support",
			href: "https://t.me/ucharmarket_support",
			color: "#229ED9",
			bg: "#E7F5FF",
		},
		{
			icon: IconPhone,
			label: t("support.phone"),
			subtitle: "+998 71 200-00-00",
			href: "tel:+998712000000",
			color: "#40C057",
			bg: "#EBFBEE",
		},
		{
			icon: IconMail,
			label: t("support.email"),
			subtitle: "support@ucharmarket.uz",
			href: "mailto:support@ucharmarket.uz",
			color: "#1A73E8",
			bg: "#E8F0FE",
		},
	];

	return (
		<SubPageLayout title={t("settings.support")}>
			{/* Info card */}
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
						fontSize: 18,
						fontWeight: 600,
						color: "#1C1C1E",
						marginBottom: 8,
					}}
				>
					{t("support.title")}
				</Text>
				<Text
					style={{
						fontSize: 15,
						color: "#8E8E93",
						lineHeight: 1.6,
					}}
				>
					{t("support.description")}
				</Text>
			</Box>

			{/* Contact channels */}
			<Box
				style={{
					backgroundColor: "#FFFFFF",
					borderRadius: 14,
					overflow: "hidden",
				}}
			>
				{channels.map((ch, i) => (
					<UnstyledButton
						key={ch.href}
						component="a"
						href={ch.href}
						target={ch.href.startsWith("http") ? "_blank" : undefined}
						rel={ch.href.startsWith("http") ? "noopener noreferrer" : undefined}
						style={{
							display: "flex",
							alignItems: "center",
							gap: 12,
							width: "100%",
							padding: 16,
							borderBottom:
								i < channels.length - 1 ? "0.5px solid #E8E8ED" : "none",
						}}
					>
						<Box
							style={{
								width: 44,
								height: 44,
								borderRadius: 12,
								backgroundColor: ch.bg,
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								flexShrink: 0,
							}}
						>
							<ch.icon size={22} color={ch.color} stroke={1.5} />
						</Box>
						<Box>
							<Text
								style={{
									fontSize: 15,
									fontWeight: 500,
									color: "#1C1C1E",
								}}
							>
								{ch.label}
							</Text>
							<Text
								style={{
									fontSize: 13,
									color: "#8E8E93",
									marginTop: 2,
								}}
							>
								{ch.subtitle}
							</Text>
						</Box>
					</UnstyledButton>
				))}
			</Box>

			{/* Hours */}
			<Box
				style={{
					backgroundColor: "#FFFFFF",
					borderRadius: 14,
					padding: 20,
					marginTop: 16,
					textAlign: "center",
				}}
			>
				<Text
					style={{
						fontSize: 14,
						color: "#8E8E93",
						lineHeight: 1.6,
					}}
				>
					{t("support.hours")}
				</Text>
			</Box>
		</SubPageLayout>
	);
}

export const Support = {
	route: "/support",
	Page,
};
