import { FC, useState } from 'react';
import { Image, Text, Stack, Skeleton, UnstyledButton, Box } from '@mantine/core';
import { useTranslation } from 'react-i18next';
import { IMAGE_BASE_URL, formatPrice, gradients } from '@app/styles/theme';
import type { BuyerListing } from '@shared/api/types';

interface MasonryListingCardProps {
  listing: BuyerListing;
  onClick: (id: string) => void;
}

export const MasonryListingCard: FC<MasonryListingCardProps> = ({ listing, onClick }) => {
  const { t } = useTranslation('buyer');
  const [imageLoaded, setImageLoaded] = useState(false);
  const formattedPrice = formatPrice(listing.price);
  const imageUrl = listing.images[0]?.imageUrl
    ? `${IMAGE_BASE_URL}${listing.images[0].imageUrl}`
    : null;

  return (
    <UnstyledButton onClick={() => onClick(listing.id)} w="100%">
      <Box
        mb={12}
        style={{
          borderRadius: 16,
          overflow: 'hidden',
          backgroundColor: 'white',
          boxShadow: '0 2px 8px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06)',
          transition: 'transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1)',
        }}
      >
        {/* Image Section */}
        <Box style={{ position: 'relative' }}>
          {/* Skeleton while loading */}
          {!imageLoaded && imageUrl && (
            <Skeleton
              height={180}
              radius={0}
              animate
              style={{ position: 'absolute', top: 0, left: 0, right: 0, zIndex: 1 }}
            />
          )}

          {/* Product Image */}
          {imageUrl ? (
            <Image
              src={imageUrl}
              alt={listing.name}
              height={180}
              fit="cover"
              style={{ opacity: imageLoaded ? 1 : 0, transition: 'opacity 0.3s ease' }}
              onLoad={() => setImageLoaded(true)}
            />
          ) : (
            <Box h={180} bg="gray.1" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Text size="xs" c="dimmed">{t('common.noImage')}</Text>
            </Box>
          )}

          {/* Gradient overlay */}
          <Box
            style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              height: '50%',
              background: gradients.cardSubtle,
              pointerEvents: 'none',
            }}
          />

          {/* Price pill on image */}
          <Box
            style={{
              position: 'absolute',
              bottom: 10,
              left: 10,
              backgroundColor: 'rgba(255,255,255,0.95)',
              backdropFilter: 'blur(8px)',
              borderRadius: 10,
              padding: '4px 10px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            }}
          >
            <Text size="sm" fw={800} c="dark.8" lh={1.3}>
              {formattedPrice} sum
            </Text>
          </Box>
        </Box>

        {/* Product Info */}
        <Stack gap={2} py={10} px={10}>
          <Text
            size="sm"
            fw={600}
            c="dark.7"
            lineClamp={1}
            style={{ fontFamily: 'var(--mantine-font-family-headings)' }}
          >
            {listing.name}
          </Text>
        </Stack>
      </Box>
    </UnstyledButton>
  );
};
