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
  // Block D D1: canonical backend identifier ("ru" | "uz" | "uz_cyrl").
  // Map to the frontend i18n locale ("uz_cyrl" → "uz-cyrl") via
  // shared/i18n/index.ts helpers when applying.
  language: 'ru' | 'uz' | 'uz_cyrl';
  seller_type: string | null;
  seller_telegram: string | null;
}
