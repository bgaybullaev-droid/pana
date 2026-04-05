import { Box, Group, Text, Badge, Menu, ActionIcon } from '@mantine/core';
import { IconExternalLink, IconDotsVertical, IconEdit } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import { ListingImageThumbnail } from '@shared/ui/ListingImageThumbnail';
import type { OLXListing } from '@shared/api/types';
import { formatPrice, radii, shadows, spacing, surface } from '@app/styles/theme';
import { getFirstImage } from './getFirstImage';
import { PropertyInfo } from './PropertyInfo';

interface OLXListingCardProps {
  listing: OLXListing;
  onClaim?: (id: string) => void;
  isClaiming?: boolean;
}

export function OLXListingCard({ listing, onClaim, isClaiming }: OLXListingCardProps) {
  const { t } = useTranslation('seller');
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
        transition: 'all 0.15s ease',
      }}
    >
      <Group wrap="nowrap" gap="md">
        <ListingImageThumbnail src={imageUrl} />
        <Box style={{ flex: 1, minWidth: 0 }}>
          <Group justify="space-between" wrap="nowrap" mb={2}>
            <Text size="lg" fw={700} truncate>
              {formatPrice(listing.price, listing.currency)}
            </Text>
            <Group gap={4} wrap="nowrap">
              <Badge variant="light" size="xs" color="teal" radius="sm">
                OLX
              </Badge>
              <Menu position="bottom-end">
                <Menu.Target>
                  <ActionIcon
                    variant="subtle"
                    radius="xl"
                    size="sm"
                    loading={isClaiming}
                    style={{ backgroundColor: 'var(--mantine-color-gray-0)' }}
                  >
                    <IconDotsVertical size={16} />
                  </ActionIcon>
                </Menu.Target>
                <Menu.Dropdown>
                  {onClaim && (
                    <Menu.Item
                      leftSection={<IconEdit size={16} />}
                      onClick={() => onClaim(listing.id)}
                    >
                      {t('listings.edit')}
                    </Menu.Item>
                  )}
                  <Menu.Item
                    leftSection={<IconExternalLink size={16} />}
                    component="a"
                    href={listing.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {t('listings.viewOnOlx')}
                  </Menu.Item>
                </Menu.Dropdown>
              </Menu>
            </Group>
          </Group>
          <Text size="sm" c="dimmed" lineClamp={1}>
            {listing.description
              ? listing.description.substring(0, 80)
              : `${listing.property_type} — ${listing.listing_type}`}
          </Text>
          <PropertyInfo listing={listing} />
          {listing.posted_date && (
            <Text size="xs" c="dimmed" mt={4}>
              {listing.posted_date}
            </Text>
          )}
        </Box>
      </Group>
    </Box>
  );
}
