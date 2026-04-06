import { Badge, Menu, ActionIcon, Group } from '@mantine/core';
import { IconExternalLink, IconDotsVertical, IconEdit } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import { ListingRow } from '@shared/ui/ListingRow';
import type { OLXListing } from '@shared/api/types';
import { getFirstImage } from './getFirstImage';

interface OLXListingCardProps {
  listing: OLXListing;
  onClaim?: (id: string) => void;
  isClaiming?: boolean;
}

export function OLXListingCard({ listing, onClaim, isClaiming }: OLXListingCardProps) {
  const { t } = useTranslation('seller');

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
      date={listing.posted_date}
      actions={
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
      }
    />
  );
}
