export const SELLER_BOT_USERNAME =
  import.meta.env.VITE_SELLER_BOT_USERNAME || 'testourbor_bot';

export const BUYER_BOT_USERNAME =
  import.meta.env.VITE_BUYER_BOT_USERNAME || 'ucharTestMarket_bot';

export const ROOMS_OPTIONS_KEYS = ['studio', '1', '2', '3', '4', '5+'] as const;

export function getListingShareUrl(listingId: string): string {
  const appLink = `https://t.me/${BUYER_BOT_USERNAME}?startapp=listing_${listingId}`;
  return `https://t.me/share/url?url=${encodeURIComponent(appLink)}`;
}
