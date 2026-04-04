export interface UserFilters {
  page?: number;
  approval_status?: string;
  role?: string;
  q?: string;
}

export interface ListingFilters {
  page?: number;
  moderation_status?: string;
  source_type?: string;
}
