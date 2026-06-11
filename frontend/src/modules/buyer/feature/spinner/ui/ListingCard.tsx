import { FC, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Text, Badge, ActionIcon, Group, Paper } from '@mantine/core';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Pagination } from 'swiper/modules';
import {
  IconHeart,
  IconHeartFilled,
  IconShare,
  IconMapPin,
  IconRuler,
  IconDoor,
  IconBuilding,
  IconPhoto,
} from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import { useTelegram } from '@app/providers/useTelegram';
import { formatPrice } from '@app/styles/theme';
import { getListingShareUrl } from '@shared/lib/constants';
import { translateDistrict } from '@shared/lib/regions';
import { rentPriceSuffixKey } from '@shared/lib/rentPriceSuffix';
import type { ListingListItem } from '@shared/api/types';

import 'swiper/css/pagination';

interface ListingCardProps {
  listing: ListingListItem;
  isActive?: boolean;
}

export const ListingCard: FC<ListingCardProps> = ({ listing }) => {
  const navigate = useNavigate();
  const { t } = useTranslation('buyer');
  const { webApp } = useTelegram();
  const [isFavorited, setIsFavorited] = useState(listing.is_favorited || false);

  const handleFavoriteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsFavorited(!isFavorited);
    // Haptic feedback
    webApp?.HapticFeedback.impactOccurred('light');
    // TODO: Call API to toggle favorite
  };

  const handleShareClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    webApp?.HapticFeedback.impactOccurred('light');
    // Share via Telegram
    webApp?.openTelegramLink(getListingShareUrl(listing.id));
  };

  const handleCardClick = () => {
    navigate(`/listings/${listing.id}`);
  };

  const propertyTypeLabels: Record<string, string> = {
    apartment: t('card.propertyType.apartment'),
    house: t('card.propertyType.house'),
    commercial: t('card.propertyType.commercial'),
    land: t('card.propertyType.land'),
  };

  const listingTypeLabels: Record<string, string> = {
    sell: t('listing.typeSell'),
    rent: t('listing.typeRent'),
  };

  // Mock images for now - replace with actual images from listing
  const images = listing.primary_image_url
    ? [listing.primary_image_url]
    : [];

  return (
    <Box
      onClick={handleCardClick}
      style={{
        height: '100%',
        width: '100%',
        position: 'relative',
        backgroundColor: '#000',
      }}
    >
      {/* Image slider or placeholder */}
      {images.length > 0 ? (
        <Swiper
          modules={[Pagination]}
          pagination={{ clickable: true }}
          style={{ height: '60%' }}
          direction="horizontal"
        >
          {images.map((url, index) => (
            <SwiperSlide key={index}>
              <Box
                style={{
                  height: '100%',
                  backgroundImage: `url(${url})`,
                  backgroundSize: 'cover',
                  backgroundPosition: 'center',
                }}
              />
            </SwiperSlide>
          ))}
        </Swiper>
      ) : (
        <Box
          style={{
            height: '60%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'var(--mantine-color-gray-2)',
          }}
        >
          <Box ta="center">
            <IconPhoto size={48} color="var(--mantine-color-gray-5)" />
            <Text c="dimmed" size="sm" mt="xs">
              {t('listing.noPhoto')}
            </Text>
          </Box>
        </Box>
      )}

      {/* Badges */}
      <Group
        gap="xs"
        style={{
          position: 'absolute',
          top: 16,
          left: 16,
          zIndex: 10,
        }}
      >
        <Badge color={listing.type === 'sell' ? 'blue' : 'green'} variant="filled">
          {listingTypeLabels[listing.type]}
        </Badge>
        {listing.is_boosted && (
          <Badge color="orange" variant="filled">
            TOP
          </Badge>
        )}
      </Group>

      {/* Action buttons */}
      <Group
        gap="xs"
        style={{
          position: 'absolute',
          top: 16,
          right: 16,
          zIndex: 10,
        }}
      >
        <ActionIcon
          variant="filled"
          color="white"
          size="lg"
          radius="xl"
          onClick={handleFavoriteClick}
          style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
        >
          {isFavorited ? (
            <IconHeartFilled size={20} color="red" />
          ) : (
            <IconHeart size={20} />
          )}
        </ActionIcon>
        <ActionIcon
          variant="filled"
          color="white"
          size="lg"
          radius="xl"
          onClick={handleShareClick}
          style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
        >
          <IconShare size={20} />
        </ActionIcon>
      </Group>

      {/* Content */}
      <Paper
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          padding: 16,
          borderRadius: '16px 16px 0 0',
          height: '45%',
        }}
      >
        {/* Price */}
        <Text size="xl" fw={700} c="blue">
          {formatPrice(listing.price, listing.currency)}
          {listing.type === 'rent' && (
            <Text span size="sm" c="dimmed" fw={400}>
              {' '}{t(rentPriceSuffixKey(listing.rent_period, listing.property_type))}
            </Text>
          )}
        </Text>

        {/* Title */}
        <Text size="lg" fw={500} lineClamp={2} mt="xs">
          {listing.title ||
            `${propertyTypeLabels[listing.property_type]}${
              listing.rooms ? `, ${listing.rooms} ${t('listing.rooms')}` : ''
            }`}
        </Text>

        {/* Location */}
        {listing.district && (
          <Group gap="xs" mt="sm">
            <IconMapPin size={16} color="var(--mantine-color-gray-6)" />
            <Text size="sm" c="dimmed">
              {translateDistrict(listing.district, t)}
            </Text>
          </Group>
        )}

        {/* Features */}
        <Group gap="md" mt="md">
          {listing.rooms !== null && (
            <Group gap={4}>
              <IconDoor size={18} color="var(--mantine-color-gray-6)" />
              <Text size="sm">{listing.rooms} {t('listing.rooms')}</Text>
            </Group>
          )}
          {listing.area !== null && (
            <Group gap={4}>
              <IconRuler size={18} color="var(--mantine-color-gray-6)" />
              <Text size="sm">{listing.area} {t('listing.area')}</Text>
            </Group>
          )}
          {listing.floor !== null && listing.total_floors !== null && (
            <Group gap={4}>
              <IconBuilding size={18} color="var(--mantine-color-gray-6)" />
              <Text size="sm">
                {listing.floor}/{listing.total_floors} {t('listing.floorLabel')}
              </Text>
            </Group>
          )}
        </Group>

        {/* Stats */}
        <Group gap="md" mt="md">
          <Text size="xs" c="dimmed">
            👁 {listing.views_count}
          </Text>
          <Text size="xs" c="dimmed">
            ❤️ {listing.favorites_count}
          </Text>
        </Group>
      </Paper>
    </Box>
  );
};
