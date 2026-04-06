import { useTranslation } from 'react-i18next';
import { ActionIcon } from '@mantine/core';
import { IconTrash } from '@tabler/icons-react';
import { radii } from '@app/styles/theme';
import { ListingRow } from '@shared/ui/ListingRow';
import type { ListingListItem } from '@shared/api/types';

interface FavoriteCardProps {
  listing: ListingListItem;
  onClick: () => void;
  onRemove: (e: React.MouseEvent) => void;
}

export function FavoriteCard({ listing, onClick, onRemove }: FavoriteCardProps) {
  const { t } = useTranslation('buyer');

  return (
    <ListingRow
      imageUrl={listing.primary_image_url}
      price={listing.price}
      currency={listing.currency}
      isRent={listing.type === 'rent'}
      description={
        listing.title ||
        `${t(`common.propertyType.${listing.property_type}`, listing.property_type)}${
          listing.rooms ? `, ${listing.rooms} ${t('common.rooms')}` : ''
        }`
      }
      rooms={listing.rooms}
      area={listing.area}
      district={listing.district}
      onClick={onClick}
      actions={
        <ActionIcon
          variant="subtle"
          color="red"
          size={32}
          radius={radii.md}
          onClick={(e) => {
            e.stopPropagation();
            onRemove(e);
          }}
          style={{ flexShrink: 0 }}
        >
          <IconTrash size={16} />
        </ActionIcon>
      }
    />
  );
}
