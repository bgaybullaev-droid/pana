import { FC } from "react";
import {
	Group,
	Avatar,
	Stack,
	Text,
	ActionIcon,
	UnstyledButton,
} from "@mantine/core";
import { IconHeart, IconCornerDownRight } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { formatTimeAgo } from "@shared/lib/date";
import type { Comment } from "@shared/api/types";

interface CommentItemProps {
	comment: Comment;
	onLike: (id: string) => void;
	onReply: (comment: Comment, topLevelCommentId?: string) => void;
	isReply?: boolean;
	topLevelCommentId?: string;
}

export const CommentItem: FC<CommentItemProps> = ({
	comment,
	onLike,
	onReply,
	isReply = false,
	topLevelCommentId,
}) => {
	const { t } = useTranslation("buyer");
	const authorName =
		comment.author.first_name +
		(comment.author.last_name ? ` ${comment.author.last_name}` : "");

	return (
		<Group align="flex-start" gap="sm" wrap="nowrap" ml={isReply ? "md" : 0}>
			{isReply && (
				<IconCornerDownRight
					size={16}
					color="var(--mantine-color-gray-5)"
					style={{ marginTop: 10 }}
				/>
			)}
			<Avatar
				src={comment.author.avatar_url}
				size={isReply ? 28 : 36}
				radius="xl"
				color="blue"
			>
				{comment.author.first_name[0]}
			</Avatar>
			<Stack gap={2} style={{ flex: 1 }}>
				<Group gap="xs">
					<Text size={isReply ? "xs" : "sm"} fw={600}>
						{authorName}
					</Text>
					<Text size="xs" c="dimmed">
						{formatTimeAgo(comment.created_at)}
					</Text>
				</Group>
				<Text size={isReply ? "xs" : "sm"} style={{ wordBreak: "break-word" }}>
					{comment.text}
				</Text>
				<Group gap="xs">
					<ActionIcon
						variant="transparent"
						size="sm"
						onClick={() => onLike(comment.id)}
					>
						<IconHeart
							size={14}
							fill={comment.is_liked ? "red" : "none"}
							color={comment.is_liked ? "red" : "gray"}
						/>
					</ActionIcon>
					{comment.likes_count > 0 && (
						<Text size="xs" c="dimmed">
							{comment.likes_count}
						</Text>
					)}
					<UnstyledButton onClick={() => onReply(comment, topLevelCommentId)}>
						<Text size="xs" c="dimmed" fw={500}>
							{t("comments.reply")}
						</Text>
					</UnstyledButton>
				</Group>
			</Stack>
		</Group>
	);
};
