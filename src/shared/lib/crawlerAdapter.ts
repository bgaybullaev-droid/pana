/**
 * Adapts crawler listing types to the ListingListItem shape
 * used by the existing UI components (ListingCard, Masonry grid, etc.).
 */
import type { ListingListItem, TelegramListing, OLXListing, UnifiedListingListItem } from '@shared/api/types';

export type ListingSource = 'main' | 'telegram' | 'olx';

export interface SourcedListingListItem extends ListingListItem {
  /** Which source this listing came from */
  _source: ListingSource;
}

const LISTING_TYPE_MAP: Record<string, 'sell' | 'rent'> = {
  sale: 'sell',
  rent: 'rent',
  daily_rent: 'rent',
};

const PROPERTY_TYPE_MAP: Record<string, 'apartment' | 'house' | 'commercial' | 'land'> = {
  apartment: 'apartment',
  house: 'house',
  commercial: 'commercial',
  land: 'land',
  office: 'commercial', // map office → commercial for UI compatibility
};

function getFirstImageUrl(images: unknown): string | null {
  if (Array.isArray(images) && images.length > 0) {
    const first = images[0];
    if (typeof first === 'string') return first;
    if (first && typeof first === 'object' && 'url' in first) return (first as any).url;
  }
  return null;
}

export function telegramToListItem(listing: TelegramListing): SourcedListingListItem {
  return {
    id: listing.id,
    type: LISTING_TYPE_MAP[listing.listing_type] || 'sell',
    property_type: PROPERTY_TYPE_MAP[listing.property_type] || 'apartment',
    rooms: listing.rooms,
    area: listing.area_sqm,
    floor: listing.floor,
    total_floors: listing.total_floors,
    region: null,
    district: listing.district,
    price: listing.price,
    currency: (listing.currency as 'USD' | 'UZS') || 'USD',
    title: listing.description?.slice(0, 200) || null,
    views_count: 0,
    favorites_count: 0,
    comments_count: 0,
    is_boosted: false,
    is_highlighted: false,
    created_at: listing.created_at,
    building_type: null,
    condition: null,
    land_purpose: null,
    primary_image_url: getFirstImageUrl(listing.images),
    _source: 'telegram',
  };
}

export function olxToListItem(listing: OLXListing): SourcedListingListItem {
  return {
    id: listing.id,
    type: LISTING_TYPE_MAP[listing.listing_type] || 'sell',
    property_type: PROPERTY_TYPE_MAP[listing.property_type] || 'apartment',
    rooms: listing.rooms,
    area: listing.area_sqm,
    floor: listing.floor,
    total_floors: listing.total_floors,
    region: null,
    district: listing.district,
    building_type: listing.building_type || null,
    condition: listing.condition || null,
    land_purpose: null,
    price: listing.price,
    currency: (listing.currency as 'USD' | 'UZS') || 'USD',
    title: listing.description?.slice(0, 200) || null,
    views_count: listing.views_count || 0,
    favorites_count: 0,
    comments_count: 0,
    is_boosted: false,
    is_highlighted: false,
    created_at: listing.created_at,
    primary_image_url: getFirstImageUrl(listing.images),
    _source: 'olx',
  };
}

export function mainToListItem(listing: ListingListItem): SourcedListingListItem {
  return { ...listing, _source: 'main' };
}

export function unifiedToListItem(item: UnifiedListingListItem): SourcedListingListItem {
  return {
    id: item.id,
    type: (item.type as 'sell' | 'rent') || 'sell',
    property_type: (item.property_type as 'apartment' | 'house' | 'commercial' | 'land') || 'apartment',
    rooms: item.rooms,
    area: item.area,
    floor: item.floor,
    total_floors: item.total_floors,
    region: item.region,
    district: item.district,
    building_type: item.building_type || null,
    condition: item.condition || null,
    land_purpose: item.land_purpose || null,
    price: item.price,
    currency: (item.currency as 'USD' | 'UZS') || 'USD',
    title: null,
    views_count: 0,
    favorites_count: 0,
    comments_count: 0,
    is_boosted: false,
    is_highlighted: false,
    created_at: item.created_at,
    primary_image_url: item.primary_image_url,
    _source: item.source,
  };
}

/**
 * Merge listings from all sources, sorted by created_at descending.
 */
export function mergeListings(
  mainListings: ListingListItem[],
  telegramListings: TelegramListing[],
  olxListings: OLXListing[],
): SourcedListingListItem[] {
  const all: SourcedListingListItem[] = [
    ...mainListings.map(mainToListItem),
    ...telegramListings.map(telegramToListItem),
    ...olxListings.map(olxToListItem),
  ];

  // Sort by created_at descending
  all.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  return all;
}

/**
 * Build the detail page URL based on listing source.
 */
export function getListingDetailUrl(item: SourcedListingListItem): string {
  return `/listings/${item.id}`;
}
