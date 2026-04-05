import { useTranslation } from "react-i18next";
import { Box, Text } from "@mantine/core";
import { PageBar } from "@shared/ui/PageBar";
import { surface } from "@app/styles/theme";

const SECTION_COUNT = 5;

function Page() {
	const { t } = useTranslation("buyer");

	return (
		<Box mih="100vh" style={{ backgroundColor: surface.page }}>
			<PageBar title={t("settings.privacy")} />
			<Box style={{ padding: 16, paddingBottom: "calc(80px + env(safe-area-inset-bottom, 0px))" }}>
			{/* Last updated */}
			<Text
				style={{
					fontSize: 13,
					color: "#8E8E93",
					marginBottom: 12,
				}}
			>
				{t("privacy.lastUpdated")}
			</Text>

			{/* Intro */}
			<Box
				style={{
					backgroundColor: "#FFFFFF",
					borderRadius: 14,
					padding: 20,
					marginBottom: 12,
				}}
			>
				<Text
					style={{
						fontSize: 14,
						color: "#3C3C43",
						lineHeight: 1.7,
					}}
				>
					{t("privacy.intro")}
				</Text>
			</Box>

			{/* Sections */}
			{Array.from({ length: SECTION_COUNT }, (_, i) => (
				<Box
					key={i}
					style={{
						backgroundColor: "#FFFFFF",
						borderRadius: 14,
						padding: 20,
						marginBottom: 12,
					}}
				>
					<Text
						style={{
							fontSize: 15,
							fontWeight: 600,
							color: "#1C1C1E",
							marginBottom: 8,
						}}
					>
						{t(`privacy.section${i + 1}Title`)}
					</Text>
					<Text
						style={{
							fontSize: 14,
							color: "#3C3C43",
							lineHeight: 1.7,
						}}
					>
						{t(`privacy.section${i + 1}Text`)}
					</Text>
				</Box>
			))}
			</Box>
		</Box>
	);
}

export const Privacy = {
	route: "/privacy",
	Page,
};
