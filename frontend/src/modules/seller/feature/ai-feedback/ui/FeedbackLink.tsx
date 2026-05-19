/**
 * Block F V2.0 (F5b) — "Не нравится текст?" trigger link.
 *
 * Renders a small inline button that opens ``FeedbackModal``. Mounted
 * from Stage 2 of the create-listing flow (once AI text appears) and
 * from the seller edit-listing page for already-published listings.
 */

import { useState } from "react";
import { Anchor } from "@mantine/core";
import { IconThumbDown } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import { FeedbackModal } from "./FeedbackModal";

interface FeedbackLinkProps {
	listingId: string;
	generationId?: string;
}

export function FeedbackLink({ listingId, generationId }: FeedbackLinkProps) {
	const { t } = useTranslation("seller");
	const [opened, setOpened] = useState(false);

	return (
		<>
			<Anchor
				component="button"
				type="button"
				onClick={() => setOpened(true)}
				underline="hover"
				c="dimmed"
				size="12px"
				style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
			>
				<IconThumbDown size={12} />
				{t("aiFeedback.linkLabel", "Не нравится текст?")}
			</Anchor>
			<FeedbackModal
				opened={opened}
				onClose={() => setOpened(false)}
				listingId={listingId}
				generationId={generationId}
			/>
		</>
	);
}
