import { Group, Text } from '@mantine/core';
import { IconDoor } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import type { OLXListing, TelegramListing } from '@shared/api/types';

export function PropertyInfo({ listing }: { listing: OLXListing | TelegramListing }) {
  const { t } = useTranslation('seller');
  const parts: string[] = [];
  if (listing.rooms) parts.push(`${listing.rooms} ${t('listings.rooms')}`);
  if (listing.area_sqm) parts.push(`${listing.area_sqm} ${t('listings.sqm')}`);
  if (listing.district) parts.push(listing.district);
  if (parts.length === 0) return null;
  return (
    <Group gap={4} wrap="nowrap">
      {listing.rooms && <IconDoor size={12} color="var(--mantine-color-gray-5)" />}
      <Text size="xs" c="dimmed" truncate>
        {parts.join(' · ')}
      </Text>
    </Group>
  );
}
