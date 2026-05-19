/**
 * Block F V2.0 (F5b) — AI feedback modal.
 *
 * Six radio categories + free-text comment. Used from Stage 2 of the
 * create-listing flow and from the seller edit page so any AI-text
 * problem can be flagged in one tap. Tracks the optional
 * ``generation_id`` so admins can join feedback rows back to the
 * specific LLM call that produced the offending text.
 */

import { useState } from "react";
import {
	Modal,
	Stack,
	Radio,
	Textarea,
	Button,
	Group,
	Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useTranslation } from "react-i18next";

import {
	submitFeedbackFx,
	type FeedbackCategory,
} from "../model";

interface FeedbackModalProps {
	opened: boolean;
	onClose: () => void;
	listingId: string;
	generationId?: string;
}

const CATEGORIES: FeedbackCategory[] = [
	"grammar",
	"unnatural",
	"factual",
	"too_long",
	"too_short",
	"other",
];

export function FeedbackModal({
	opened,
	onClose,
	listingId,
	generationId,
}: FeedbackModalProps) {
	const { t } = useTranslation("seller");
	const [category, setCategory] = useState<FeedbackCategory>("grammar");
	const [comment, setComment] = useState("");
	const [submitting, setSubmitting] = useState(false);

	const handleClose = () => {
		// Don't reset state on submit-success — useEffect on opened toggle
		// would race. Reset only on user-initiated dismiss.
		setComment("");
		setCategory("grammar");
		onClose();
	};

	const handleSubmit = async () => {
		setSubmitting(true);
		try {
			await submitFeedbackFx({
				listing_id: listingId,
				generation_id: generationId,
				category,
				comment: comment.trim() || undefined,
			});
			notifications.show({
				title: t("notifications.success"),
				message: t(
					"aiFeedback.submitted",
					"Спасибо, передали в команду качества.",
				),
				color: "green",
			});
			handleClose();
		} catch (err: unknown) {
			const status = (err as { response?: { status?: number } })?.response
				?.status;
			notifications.show({
				title: t("notifications.error"),
				message:
					status === 429
						? t(
								"aiFeedback.rateLimited",
								"Слишком много отзывов. Попробуйте через минуту.",
							)
						: t("aiFeedback.submitFailed", "Не удалось отправить отзыв."),
				color: "red",
			});
		} finally {
			setSubmitting(false);
		}
	};

	return (
		<Modal
			opened={opened}
			onClose={handleClose}
			title={t("aiFeedback.title", "Что не так с текстом?")}
			centered
			size="md"
		>
			<Stack gap="md">
				<Text size="13px" c="dimmed">
					{t(
						"aiFeedback.intro",
						"Опишите, в чём проблема — это помогает улучшить генерацию для всех.",
					)}
				</Text>
				<Radio.Group
					value={category}
					onChange={(v) => setCategory(v as FeedbackCategory)}
				>
					<Stack gap="xs">
						{CATEGORIES.map((c) => (
							<Radio
								key={c}
								value={c}
								label={t(
									`aiFeedback.category.${c}`,
									_DEFAULT_CATEGORY_LABELS[c],
								)}
							/>
						))}
					</Stack>
				</Radio.Group>
				<Textarea
					placeholder={t(
						"aiFeedback.commentPlaceholder",
						"Подробности (необязательно)",
					)}
					value={comment}
					onChange={(e) => setComment(e.currentTarget.value)}
					minRows={3}
					maxRows={6}
					maxLength={2000}
					autosize
				/>
				<Group justify="flex-end" gap="sm">
					<Button variant="subtle" onClick={handleClose}>
						{t("aiFeedback.cancel", "Отмена")}
					</Button>
					<Button color="blue" loading={submitting} onClick={handleSubmit}>
						{t("aiFeedback.submit", "Отправить")}
					</Button>
				</Group>
			</Stack>
		</Modal>
	);
}

const _DEFAULT_CATEGORY_LABELS: Record<FeedbackCategory, string> = {
	grammar: "Грамматические ошибки",
	unnatural: "Звучит неестественно",
	factual: "Неверные факты",
	too_long: "Слишком длинно",
	too_short: "Слишком коротко",
	other: "Другое",
};
