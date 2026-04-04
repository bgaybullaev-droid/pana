import { Box } from "@mantine/core";
import { IconSparkles } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { GradientHeader } from "@shared/ui/GradientHeader";
import { PreferencesPanel } from "@modules/buyer/feature/preferences";

function Page() {
	const { t } = useTranslation("buyer");
	const navigate = useNavigate();

	return (
		<Box mih="100vh" bg="#f8f9fa">
			<GradientHeader
				icon={IconSparkles}
				title={t("preferences.title")}
				onBack={() => navigate(-1)}
			/>

			<Box style={{ marginTop: -30, position: "relative", zIndex: 1 }}>
				<PreferencesPanel />
			</Box>
		</Box>
	);
}

export const Preferences = {
	route: "/preferences",
	Page,
};
