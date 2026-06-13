import { Button, Modal, Stack, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { useTelegramBackClose } from "@shared/hooks/useTelegramBackClose";

/**
 * Block D D4 — shared "photo cannot be edited" modal.
 *
 * Telegram forbids photo changes on channel posts older than 48 h. The API
 * answers ``media_too_old`` to an update call; this modal offers the three
 * resolutions (text-only edit / delete + repost / cancel). Used both on the
 * Autoposting page and on "My listings" so the copy stays in one place.
 */
interface MediaCutoffModalProps {
	opened: boolean;
	/** Age of the post in hours, surfaced in the body copy. */
	postAgeHours: number | null;
	onTextOnly: () => void;
	onRecreate: () => void;
	onCancel: () => void;
}

export function MediaCutoffModal({
	opened,
	postAgeHours,
	onTextOnly,
	onRecreate,
	onCancel,
}: MediaCutoffModalProps) {
	const { t } = useTranslation("seller");
	useTelegramBackClose(opened, onCancel);

	return (
		<Modal
			opened={opened}
			onClose={onCancel}
			title={t("autopost.media_modal_title", "Photo cannot be edited")}
			centered
		>
			<Stack gap="md">
				<Text size="sm">
					{t("autopost.media_modal_body", {
						hours: postAgeHours ?? "?",
						defaultValue:
							"Telegram does not allow photo changes on posts older than 48 hours (this post is {{hours}}h old). What would you like to do?",
					})}
				</Text>
				<Stack gap="xs">
					<Button fullWidth variant="light" onClick={onTextOnly}>
						{t("autopost.media_modal_text_only", "Update text only")}
					</Button>
					<Button fullWidth variant="light" color="red" onClick={onRecreate}>
						{t(
							"autopost.media_modal_recreate",
							"Delete old post and publish a new one",
						)}
					</Button>
					<Button fullWidth variant="subtle" onClick={onCancel}>
						{t("autopost.media_modal_cancel", "Cancel")}
					</Button>
				</Stack>
			</Stack>
		</Modal>
	);
}
