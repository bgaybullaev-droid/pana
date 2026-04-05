import { Box, Group, Text, Badge } from '@mantine/core';
import { ListingImageThumbnail } from '@shared/ui/ListingImageThumbnail';
import type { TelegramListing } from '@shared/api/types';
import { formatPrice, radii, shadows, spacing, surface } from '@app/styles/theme';
import { getFirstImage } from './getFirstImage';
import { PropertyInfo } from './PropertyInfo';

export function TelegramListingCard({ listing }: { listing: TelegramListing }) {
  const imageUrl = getFirstImage(listing.images);

  return (
    <Box
      style={{
        backgroundColor: surface.card,
        borderRadius: radii.md,
        padding: spacing.cardCompact,
        boxShadow: shadows.sm,
        border: '1px dashed var(--mantine-color-gray-3)',
        position: 'relative',
      }}
    >
      <Group wrap="nowrap" gap="md">
        <ListingImageThumbnail src={imageUrl} />
        <Box style={{ flex: 1, minWidth: 0 }}>
          <Group justify="space-between" wrap="nowrap" mb={2}>
            <Text size="lg" fw={700} truncate>
              {formatPrice(listing.price, listing.currency)}
            </Text>
            <Badge variant="light" size="xs" color="blue" radius="sm">
              Telegram
            </Badge>
          </Group>
          <Text size="sm" c="dimmed" lineClamp={1}>
            {listing.description
              ? listing.description.substring(0, 80)
              : `${listing.property_type} — ${listing.listing_type}`}
          </Text>
          <PropertyInfo listing={listing} />
          {listing.source_channel && (
            <Text size="xs" c="blue.5" mt={4}>
              {listing.source_channel}
            </Text>
          )}
        </Box>
      </Group>
    </Box>
  );
}
