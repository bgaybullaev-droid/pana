import { useTranslation } from "react-i18next";
import { InnerPage } from "@shared/ui/InnerPage";
import { PreferencesPanel } from "@modules/buyer/feature/preferences";

function Page() {
	const { t } = useTranslation("buyer");

	return (
		<InnerPage title={t("preferences.title")} noPadding>
			<PreferencesPanel />
		</InnerPage>
	);
}

export const Preferences = {
	route: "/preferences",
	Page,
};
