import { Box } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { PageBar } from "@shared/ui/PageBar";
import { PreferencesPanel } from "@modules/buyer/feature/preferences";
import { surface } from "@app/styles/theme";

function Page() {
	const { t } = useTranslation("buyer");

	return (
		<Box mih="100vh" style={{ backgroundColor: surface.page }}>
			<PageBar title={t("preferences.title")} />
			<PreferencesPanel />
		</Box>
	);
}

export const Preferences = {
	route: "/preferences",
	Page,
};
