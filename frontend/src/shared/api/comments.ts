import { apiClient } from './client';
import type { Comment, CommentCreateRequest, PaginatedResponse } from './types';

export const commentsApi = {
  // Get comments for a listing
  getComments: async (listingId: string, page = 1, perPage = 20) => {
    const response = await apiClient.get<PaginatedResponse<Comment>>(
      `/listings/${listingId}/comments`,
      {
        params: { page, per_page: perPage },
      }
    );
    return response.data;
  },

  // Create a new comment
  createComment: async (listingId: string, data: CommentCreateRequest) => {
    const response = await apiClient.post<Comment>(
      `/listings/${listingId}/comments`,
      data
    );
    return response.data;
  },

  // Get replies for a comment
  getReplies: async (listingId: string, commentId: string, page = 1, perPage = 20) => {
    const response = await apiClient.get<PaginatedResponse<Comment>>(
      `/listings/${listingId}/comments/${commentId}/replies`,
      {
        params: { page, per_page: perPage },
      }
    );
    return response.data;
  },

  // Delete a comment
  deleteComment: async (listingId: string, commentId: string) => {
    await apiClient.delete(`/listings/${listingId}/comments/${commentId}`);
  },

  // Like a comment
  likeComment: async (listingId: string, commentId: string) => {
    await apiClient.post(`/listings/${listingId}/comments/${commentId}/like`);
  },

  // Unlike a comment
  unlikeComment: async (listingId: string, commentId: string) => {
    await apiClient.delete(`/listings/${listingId}/comments/${commentId}/like`);
  },
};
