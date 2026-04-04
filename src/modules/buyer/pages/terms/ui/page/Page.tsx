import { useTranslation } from "react-i18next";
import { Box, Text } from "@mantine/core";
import { SubPageLayout } from "@shared/ui/SubPageLayout";

const SECTION_COUNT = 6;

function Page() {
	const { t } = useTranslation("buyer");

	return (
		<SubPageLayout title={t("settings.terms")}>
			{/* Last updated */}
			<Text
				style={{
					fontSize: 13,
					color: "#8E8E93",
					marginBottom: 12,
				}}
			>
				{t("terms.lastUpdated")}
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
					{t("terms.intro")}
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
						{t(`terms.section${i + 1}Title`)}
					</Text>
					<Text
						style={{
							fontSize: 14,
							color: "#3C3C43",
							lineHeight: 1.7,
						}}
					>
						{t(`terms.section${i + 1}Text`)}
					</Text>
				</Box>
			))}
		</SubPageLayout>
	);
}

export const Terms = {
	route: "/terms",
	Page,
};
