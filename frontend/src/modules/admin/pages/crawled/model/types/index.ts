export interface CrawledStats {
  olx_count: number;
  telegram_count: number;
}

export type CrawledSource = 'all' | 'olx' | 'telegram';

export interface CrawledFilters {
  source: CrawledSource;
  page: number;
  property_type?: string;
  listing_type?: string;
}
