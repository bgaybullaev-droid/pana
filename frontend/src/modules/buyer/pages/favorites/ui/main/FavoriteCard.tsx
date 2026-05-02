import { useTranslation } from 'react-i18next';
import { ActionIcon, Badge, Group, Stack, Text } from '@mantine/core';
import { IconTrash, IconMapPin, IconRuler, IconBed, IconBuilding } from '@tabler/icons-react';
import { radii } from '@app/styles/theme';
import { ListingRow } from '@shared/ui/ListingRow';
import type { ListingListItem } from '@shared/api/types';
import { translateDistrict, translateRegion, getRegionForDistrict } from '@shared/lib/regions';

interface FavoriteCardProps {
  listing: ListingListItem;
  onClick: () => void;
  onRemove: (e: React.MouseEvent) => void;
}

export function FavoriteCard({ listing, onClick, onRemove }: FavoriteCardProps) {
  const { t } = useTranslation('buyer');

  // Labels
  const propertyLabel = t(
    `card.propertyType.${listing.property_type}`,
    t(`common.propertyType.${listing.property_type}`, listing.property_type)
  );

  const KNOWN_BUILDING_TYPES = ["new", "secondary"];
  let buildingTypeStr = null;
  if (
    listing.building_type &&
    KNOWN_BUILDING_TYPES.includes(listing.building_type)
  ) {
    buildingTypeStr = t(`listing.buildingType.${listing.building_type}`);
  }

  // Location
  let actualRegionKey = listing.region;
  if (!actualRegionKey && listing.district) {
    actualRegionKey = getRegionForDistrict(listing.district) || null;
  }
  const regionLabel = translateRegion(actualRegionKey, t);
  const districtRawLabel = translateDistrict(listing.district, t);

  const locationParts = [];
  if (regionLabel && regionLabel !== districtRawLabel) {
    locationParts.push(regionLabel);
  }
  if (districtRawLabel) {
    locationParts.push(districtRawLabel);
  }
  const fullLocationLabel = locationParts.length > 0 ? locationParts.join(", ") : t("listing.defaultDistrict");

  // Condition
  const KNOWN_CONDITIONS = ["euro", "cosmetic", "needs_repair", "rough"];
  let conditionStr = null;
  if (
    listing.condition &&
    KNOWN_CONDITIONS.includes(listing.condition)
  ) {
    conditionStr = t(`listing.condition.${listing.condition}`);
  }

  return (
    <ListingRow
      imageUrl={listing.primary_image_url}
      price={listing.price}
      currency={listing.currency}
      isRent={listing.type === 'rent'}
      description={null}
      rooms={null}
      area={null}
      district={null}
      onClick={onClick}
      actions={
        <Group gap={8} wrap="nowrap" align="center">
          <Badge
            size="sm"
            variant="filled"
            radius="sm"
            style={{
              backgroundColor: listing.type === 'sell' ? 'rgba(34,139,230,0.9)' : 'rgba(64,192,87,0.9)',
              textTransform: 'none',
              fontWeight: 700,
            }}
          >
            {listing.type === "sell" ? t("common.sell") : t("common.rent")}
          </Badge>
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
        </Group>
      }
    >
      <Stack gap={4} mt={6}>
        {/* Row 1: Title (Property Type + Building Type) */}
        <Text size="sm" fw={600} c="dark.7" truncate style={{ fontFamily: "var(--mantine-font-family-headings)" }}>
          {propertyLabel}
          {buildingTypeStr && (
            <Text span c="gray.6" fw={500}>
              {`, ${buildingTypeStr.toLowerCase()}`}
            </Text>
          )}
        </Text>

        {/* Row 2: Location */}
        <Group gap={4} wrap="nowrap" style={{ minWidth: 0, overflow: "hidden" }}>
          <IconMapPin size={14} color="var(--mantine-color-gray-5)" stroke={2} style={{ flexShrink: 0 }} />
          <Text size="xs" c="gray.6" fw={500} truncate>
            {fullLocationLabel}
          </Text>
        </Group>

        {/* Row 3: Specs (Area, Rooms, Floor) */}
        <Group gap={8} wrap="nowrap" style={{ minWidth: 0, overflow: "hidden" }}>
          {listing.area != null && (
            <Group gap={3} wrap="nowrap" style={{ flexShrink: 0 }}>
              <IconRuler size={14} color="var(--mantine-color-gray-5)" stroke={2} />
              <Text size="xs" c="gray.6" fw={500}>
                {listing.area} {t("common.sqm")}
              </Text>
            </Group>
          )}
          {listing.rooms != null && (
            <Group gap={3} wrap="nowrap" style={{ flexShrink: 0 }}>
              <IconBed size={14} color="var(--mantine-color-gray-5)" stroke={2} />
              <Text size="xs" c="gray.6" fw={500}>
                {listing.rooms} {t("common.rooms")}
              </Text>
            </Group>
          )}
          {(listing.floor != null || listing.total_floors != null) && (
            <Group gap={3} wrap="nowrap" style={{ flexShrink: 0 }}>
              <IconBuilding size={14} color="var(--mantine-color-gray-5)" stroke={2} />
              <Text size="xs" c="gray.6" fw={500}>
                {listing.floor || "?"}/{listing.total_floors || "?"}
              </Text>
            </Group>
          )}
        </Group>

        {/* Row 4: Condition */}
        {conditionStr && (
          <Text size="xs" c="blue.5" fw={500} truncate>
            {conditionStr}
          </Text>
        )}
      </Stack>
    </ListingRow>
  );
}
