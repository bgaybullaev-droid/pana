import { FC, useState, useEffect, useCallback, useRef } from 'react';
import {
  Drawer,
  Box,
  Text,
  Stack,
  Group,
  TextInput,
  ActionIcon,
  ScrollArea,
  Loader,
  Center,
  Collapse,
  UnstyledButton,
} from '@mantine/core';
import { IconSend, IconX } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import { commentsApi } from '@shared/api/comments';
import type { Comment } from '@shared/api/types';
import { CommentItem } from '../main/CommentItem';

interface CommentsDrawerProps {
  opened: boolean;
  onClose: () => void;
  listingId: string;
  onCommentAdded?: () => void;
}

interface CommentWithReplies extends Comment {
  loadedReplies?: Comment[];
  repliesExpanded?: boolean;
}

export const CommentsDrawer: FC<CommentsDrawerProps> = ({
  opened,
  onClose,
  listingId,
  onCommentAdded,
}) => {
  const { t } = useTranslation('buyer');
  const [comments, setComments] = useState<CommentWithReplies[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [replyingTo, setReplyingTo] = useState<Comment | null>(null);
  const [replyingToTopLevelId, setReplyingToTopLevelId] = useState<string | null>(null);
  const [loadingReplies, setLoadingReplies] = useState<Set<string>>(new Set());
  const lastLoadedForRef = useRef<string | null>(null);

  const loadComments = useCallback(async (pageNum: number, reset = false) => {
    if (!listingId) return;

    setIsLoading(true);
    try {
      const response = await commentsApi.getComments(listingId, pageNum);
      setComments((prev) =>
        reset ? response.items : [...prev, ...response.items]
      );
      setHasMore(response.page < response.total_pages);
      setPage(pageNum);
    } catch (error) {
      console.error('Failed to load comments:', error);
    } finally {
      setIsLoading(false);
    }
  }, [listingId]);

  useEffect(() => {
    if (opened && listingId) {
      // Prevent double call in React StrictMode - only load if not already loaded for this listing
      const loadKey = `${listingId}-${opened}`;
      if (lastLoadedForRef.current !== loadKey) {
        lastLoadedForRef.current = loadKey;
        loadComments(1, true);
        setReplyingTo(null);
        setReplyingToTopLevelId(null);
        setNewComment('');
      }
    } else if (!opened) {
      // Reset when drawer closes so we can reload when it opens again
      lastLoadedForRef.current = null;
    }
  }, [opened, listingId, loadComments]);

  const loadReplies = async (commentId: string) => {
    const comment = comments.find((c) => c.id === commentId);
    if (!comment) return;

    // Toggle if already expanded
    if (comment.repliesExpanded) {
      setComments((prev) =>
        prev.map((c) =>
          c.id === commentId ? { ...c, repliesExpanded: false } : c
        )
      );
      return;
    }

    // Load replies if not already loaded
    if (!comment.loadedReplies) {
      setLoadingReplies((prev) => new Set(prev).add(commentId));
      try {
        const response = await commentsApi.getReplies(listingId, commentId);
        setComments((prev) =>
          prev.map((c) =>
            c.id === commentId
              ? { ...c, loadedReplies: response.items, repliesExpanded: true }
              : c
          )
        );
      } catch (error) {
        console.error('Failed to load replies:', error);
      } finally {
        setLoadingReplies((prev) => {
          const next = new Set(prev);
          next.delete(commentId);
          return next;
        });
      }
    } else {
      // Just expand if already loaded
      setComments((prev) =>
        prev.map((c) =>
          c.id === commentId ? { ...c, repliesExpanded: true } : c
        )
      );
    }
  };

  const handleSubmit = async () => {
    if (!newComment.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const comment = await commentsApi.createComment(listingId, {
        text: newComment.trim(),
        parent_id: replyingTo?.id,
      });

      if (replyingTo) {
        // Determine which top-level comment to update
        // If replying to a reply, use replyingToTopLevelId, otherwise use replyingTo.id
        const topLevelId = replyingToTopLevelId || replyingTo.id;

        // Add reply to the top-level comment's replies
        setComments((prev) =>
          prev.map((c) =>
            c.id === topLevelId
              ? {
                  ...c,
                  replies_count: c.replies_count + 1,
                  loadedReplies: c.loadedReplies
                    ? [...c.loadedReplies, comment]
                    : [comment],
                  repliesExpanded: true,
                }
              : c
          )
        );
        setReplyingTo(null);
        setReplyingToTopLevelId(null);
      } else {
        // Add new top-level comment
        setComments((prev) => [comment, ...prev]);
      }
      setNewComment('');
      // Notify parent that a comment was added
      onCommentAdded?.();
    } catch (error) {
      console.error('Failed to post comment:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLike = async (commentId: string) => {
    // Find comment in top-level or replies
    let comment: Comment | undefined = comments.find((c) => c.id === commentId);
    let isReply = false;
    let parentId: string | undefined;

    if (!comment) {
      for (const c of comments) {
        const reply = c.loadedReplies?.find((r) => r.id === commentId);
        if (reply) {
          comment = reply;
          isReply = true;
          parentId = c.id;
          break;
        }
      }
    }

    if (!comment) return;

    try {
      if (comment.is_liked) {
        await commentsApi.unlikeComment(listingId, commentId);
      } else {
        await commentsApi.likeComment(listingId, commentId);
      }

      const updateComment = (c: Comment): Comment =>
        c.id === commentId
          ? {
              ...c,
              is_liked: !c.is_liked,
              likes_count: c.is_liked ? c.likes_count - 1 : c.likes_count + 1,
            }
          : c;

      setComments((prev) =>
        prev.map((c) => {
          if (isReply && c.id === parentId) {
            return {
              ...c,
              loadedReplies: c.loadedReplies?.map(updateComment),
            };
          }
          return updateComment(c) as CommentWithReplies;
        })
      );
    } catch (error) {
      console.error('Failed to toggle like:', error);
    }
  };

  const handleReply = (comment: Comment, topLevelCommentId?: string) => {
    setReplyingTo(comment);
    // If topLevelCommentId is provided, this is a reply to a reply
    // Otherwise, this is a reply to a top-level comment
    setReplyingToTopLevelId(topLevelCommentId || null);
  };

  const cancelReply = () => {
    setReplyingTo(null);
    setReplyingToTopLevelId(null);
    setNewComment('');
  };

  const handleLoadMore = () => {
    if (!isLoading && hasMore) {
      loadComments(page + 1);
    }
  };

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      position="bottom"
      size="70%"
      withCloseButton={false}
      styles={{
        content: {
          borderTopLeftRadius: 16,
          borderTopRightRadius: 16,
        },
        body: {
          padding: 0,
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
        },
      }}
    >
      {/* Header */}
      <Box px="md" py="sm" style={{ borderBottom: '1px solid var(--mantine-color-gray-2)' }}>
        <Group justify="space-between" align="center">
          <Text fw={600} size="lg">
            {t('comments.title')}
          </Text>
          <ActionIcon variant="subtle" onClick={onClose}>
            <IconX size={20} />
          </ActionIcon>
        </Group>
      </Box>

      {/* Comments List */}
      <ScrollArea style={{ flex: 1 }} px="md" py="sm">
        {isLoading && comments.length === 0 ? (
          <Center py="xl">
            <Loader size="sm" />
          </Center>
        ) : comments.length === 0 ? (
          <Center py="xl">
            <Text c="dimmed">{t('comments.empty')}</Text>
          </Center>
        ) : (
          <Stack gap="md">
            {comments.map((comment) => (
              <Box key={comment.id}>
                <CommentItem
                  comment={comment}
                  onLike={handleLike}
                  onReply={handleReply}
                />
                {/* View replies button */}
                {comment.replies_count > 0 && (
                  <UnstyledButton
                    onClick={() => loadReplies(comment.id)}
                    ml={48}
                    mt={4}
                  >
                    <Group gap={4}>
                      {loadingReplies.has(comment.id) ? (
                        <Loader size={12} />
                      ) : (
                        <Text size="xs" c="blue" fw={500}>
                          {comment.repliesExpanded
                            ? t('comments.hideReplies')
                            : t('comments.showReplies', { count: comment.replies_count })}
                        </Text>
                      )}
                    </Group>
                  </UnstyledButton>
                )}
                {/* Replies */}
                <Collapse in={comment.repliesExpanded || false}>
                  <Stack gap="sm" mt="sm" ml="md">
                    {comment.loadedReplies?.map((reply) => (
                      <CommentItem
                        key={reply.id}
                        comment={reply}
                        onLike={handleLike}
                        onReply={handleReply}
                        isReply
                        topLevelCommentId={comment.id}
                      />
                    ))}
                  </Stack>
                </Collapse>
              </Box>
            ))}
            {hasMore && (
              <Center>
                <Text
                  size="sm"
                  c="blue"
                  style={{ cursor: 'pointer' }}
                  onClick={handleLoadMore}
                >
                  {isLoading ? t('comments.loading') : t('comments.loadMore')}
                </Text>
              </Center>
            )}
          </Stack>
        )}
      </ScrollArea>

      {/* Input Area */}
      <Box
        px="md"
        py="sm"
        style={{
          borderTop: '1px solid var(--mantine-color-gray-2)',
          paddingBottom: 'calc(12px + env(safe-area-inset-bottom, 0px))',
        }}
      >
        {/* Reply indicator */}
        {replyingTo && (
          <Group gap="xs" mb="xs">
            <Text size="xs" c="dimmed">
              {t('comments.replyTo', { name: replyingTo.author.first_name })}
            </Text>
            <ActionIcon size="xs" variant="subtle" onClick={cancelReply}>
              <IconX size={12} />
            </ActionIcon>
          </Group>
        )}
        <Group gap="sm">
          <TextInput
            placeholder={replyingTo ? t('comments.replyPlaceholder') : t('comments.placeholder')}
            value={newComment}
            onChange={(e) => setNewComment(e.currentTarget.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            style={{ flex: 1 }}
            disabled={isSubmitting}
          />
          <ActionIcon
            variant="filled"
            color="blue"
            size="lg"
            onClick={handleSubmit}
            loading={isSubmitting}
            disabled={!newComment.trim()}
          >
            <IconSend size={18} />
          </ActionIcon>
        </Group>
      </Box>
    </Drawer>
  );
};
