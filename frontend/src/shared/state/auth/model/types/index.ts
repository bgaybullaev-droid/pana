export interface AuthUser {
  id: string;
  telegram_id: number | null;
  first_name: string;
  last_name: string | null;
  username: string | null;
  avatar_url: string | null;
  role: string;
  is_seller: boolean;
  onboarding_completed: boolean;
  approval_status: 'pending' | 'approved' | 'rejected';
  auth_source: string | null;
  phone: string | null;
}
