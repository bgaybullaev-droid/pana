import { Badge } from '@mantine/core';
import { ListingRow } from '@shared/ui/ListingRow';
import type { TelegramListing } from '@shared/api/types';
import { getFirstImage } from './getFirstImage';

export function TelegramListingCard({ listing }: { listing: TelegramListing }) {
  return (
    <ListingRow
      imageUrl={getFirstImage(listing.images)}
      price={listing.price}
      currency={listing.currency}
      isRent={listing.listing_type === 'rent'}
      description={listing.description?.substring(0, 80) || `${listing.property_type} — ${listing.listing_type}`}
      rooms={listing.rooms}
      area={listing.area_sqm}
      district={listing.district}
      date={listing.source_channel || undefined}
      actions={
        <Badge variant="light" size="xs" color="blue" radius="sm">
          Telegram
        </Badge>
      }
    />
  );
}
