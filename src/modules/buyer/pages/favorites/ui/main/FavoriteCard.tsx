import { useTranslation } from 'react-i18next';
import { Box, Text, Group, Image, ActionIcon, UnstyledButton } from '@mantine/core';
import { IconTrash, IconPhoto, IconBed, IconRuler } from '@tabler/icons-react';
import { formatPrice, propertyTypeColors, shadows, transitions } from '@app/styles/theme';
import { translateDistrict } from '@shared/lib/regions';
import type { ListingListItem } from '@shared/api/types';

interface FavoriteCardProps {
  listing: ListingListItem;
  onClick: () => void;
  onRemove: (e: React.MouseEvent) => void;
}

export function FavoriteCard({ listing, onClick, onRemove }: FavoriteCardProps) {
  const { t } = useTranslation('buyer');
  const typeColor = propertyTypeColors[listing.property_type] || '#228be6';

  return (
    <UnstyledButton onClick={onClick} style={{ display: 'block' }}>
      <Box
        style={{
          backgroundColor: 'white',
          borderRadius: 16,
          boxShadow: shadows.card,
          overflow: 'hidden',
          transition: transitions.spring,
        }}
      >
        <Group wrap="nowrap" gap={0}>
          {/* Image */}
          <Box
            style={{
              width: 120,
              height: 100,
              flexShrink: 0,
              backgroundColor: '#f1f3f5',
              position: 'relative',
            }}
          >
            {listing.primary_image_url ? (
              <Image
                src={listing.primary_image_url}
                alt=""
                w={120}
                h={100}
                fit="cover"
              />
            ) : (
              <Box
                style={{
                  width: '100%', height: '100%',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
              >
                <IconPhoto size={24} color="#ced4da" />
              </Box>
            )}
            {/* Property type tag */}
            <Box
              style={{
                position: 'absolute',
                top: 8,
                left: 8,
                backgroundColor: typeColor,
                borderRadius: 6,
                padding: '2px 6px',
              }}
            >
              <Text style={{ fontSize: 9, fontWeight: 700, color: 'white', lineHeight: 1.3 }}>
                {t(`common.propertyType.${listing.property_type}`, listing.property_type)}
              </Text>
            </Box>
          </Box>

          {/* Content */}
          <Box style={{ flex: 1, minWidth: 0, padding: '10px 12px' }}>
            <Group justify="space-between" wrap="nowrap" mb={4}>
              <Text size="md" fw={800} c="blue.7" truncate>
                {formatPrice(listing.price, listing.currency)}
                {listing.type === 'rent' && (
                  <Text span size="xs" fw={500} c="dimmed">{t('common.perMonth')}</Text>
                )}
              </Text>
              <ActionIcon
                variant="subtle"
                color="red"
                size={32}
                radius={10}
                onClick={onRemove}
                style={{ flexShrink: 0 }}
              >
                <IconTrash size={16} />
              </ActionIcon>
            </Group>

            <Text size="sm" fw={500} truncate c="dark.6">
              {listing.title ||
                `${t(`common.propertyType.${listing.property_type}`, listing.property_type)}${
                  listing.rooms ? `, ${listing.rooms} ${t('common.rooms')}` : ''
                }`}
            </Text>

            {listing.district && (
              <Text size="xs" c="dimmed" truncate mt={2}>
                {translateDistrict(listing.district, t)}
              </Text>
            )}

            <Group gap={10} mt={6}>
              {listing.rooms !== null && (
                <Group gap={3}>
                  <IconBed size={12} color="#adb5bd" stroke={2} />
                  <Text size="xs" c="gray.6" fw={500}>{listing.rooms}</Text>
                </Group>
              )}
              {listing.area !== null && (
                <Group gap={3}>
                  <IconRuler size={12} color="#adb5bd" stroke={2} />
                  <Text size="xs" c="gray.6" fw={500}>{listing.area} {t('common.sqm')}</Text>
                </Group>
              )}
            </Group>
          </Box>
        </Group>
      </Box>
    </UnstyledButton>
  );
}
