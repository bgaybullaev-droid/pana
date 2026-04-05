import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUnit } from 'effector-react';
import {
  Container,
  Stack,
  Text,
  Group,
  Badge,
  Menu,
  ActionIcon,
  Box,
  Modal,
  Skeleton,
  Button,
  Card,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconPlus,
  IconDotsVertical,
  IconEdit,
  IconPlayerPause,
  IconPlayerPlay,
  IconTrash,
  IconEye,
  IconPhone,
  IconExternalLink,
  IconBuilding,
} from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import { InnerPage } from '@shared/ui/InnerPage';
import {
  $sellerListings,
  $isLoadingListings,
  fetchSellerListings,
  pauseListing,
  activateListing,
  deleteListing,
  pauseListingFx,
  activateListingFx,
  deleteListingFx,
} from '@modules/seller/shared/state';
import type { OLXListing, TelegramListing } from '@shared/api/types';
import {
  fetchSellerOLXListings,
  fetchSellerTelegramListings,
  claimOlxListing,
} from '@shared/api/sellerCrawledListings';
import { EmptyState } from '@shared/ui/EmptyState';
import { PillTabs } from '@shared/ui/PillTabs';
import { ListingImageThumbnail } from '@shared/ui/ListingImageThumbnail';
import { formatPrice, radii, shadows, surface } from '@app/styles/theme';
import { translateDistrict } from '@shared/lib/regions';

interface UnifiedCard {
  id: string;
  rawId?: string; // Original UUID for OLX listings (without prefix)
  source: 'platform' | 'olx' | 'telegram';
  price: number;
  currency: string;
  title: string;
  imageUrl: string | null;
  rooms: number | null;
  area: number | null;
  district: string | null;
  status?: string;
  views_count?: number;
  contacts_count?: number;
  externalUrl?: string;
  postedDate?: string | null;
  sourceChannel?: string | null;
}

const statusColors: Record<string, string> = {
  active: '#40c057',
  paused: '#fab005',
  sold: '#adb5bd',
  expired: '#fa5252',
  pending: '#228be6',
};

const sourceColors: Record<string, string> = {
  platform: 'blue',
  olx: 'teal',
  telegram: 'cyan',
};

function Page() {
  const navigate = useNavigate();
  const { t } = useTranslation('seller');
  const [filter, setFilter] = useState('all');
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [listingToDelete, setListingToDelete] = useState<string | null>(null);
  const [listings, isLoading] = useUnit([$sellerListings, $isLoadingListings]);

  const [olxListings, setOlxListings] = useState<OLXListing[]>([]);
  const [telegramListings, setTelegramListings] = useState<TelegramListing[]>([]);
  const [isCrawledLoading, setIsCrawledLoading] = useState(true);
  const [olxTotal, setOlxTotal] = useState(0);
  const [telegramTotal, setTelegramTotal] = useState(0);

  const statusLabels: Record<string, string> = {
    active: t('listings.statusActive'),
    paused: t('listings.statusPaused'),
    sold: t('listings.statusSold'),
    expired: t('listings.statusExpired'),
    pending: t('listings.statusPending'),
  };

  const sourceLabels: Record<string, string> = {
    platform: t('listings.platform'),
    olx: 'OLX',
    telegram: 'Telegram',
  };

  useEffect(() => {
    fetchSellerListings({});
  }, []);

  useEffect(() => {
    setIsCrawledLoading(true);
    Promise.all([
      fetchSellerOLXListings({ page: 1, per_page: 100 }).catch(() => ({ items: [], total: 0 })),
      fetchSellerTelegramListings({ page: 1, per_page: 100 }).catch(() => ({ items: [], total: 0 })),
    ]).then(([olx, tg]) => {
      setOlxListings(olx.items);
      setOlxTotal(olx.total);
      setTelegramListings(tg.items);
      setTelegramTotal(tg.total);
      setIsCrawledLoading(false);
    });
  }, []);

  useEffect(() => {
    const unwatchPause = pauseListingFx.doneData.watch(() => {
      notifications.show({ title: t('notifications.done'), message: t('notifications.paused'), color: 'yellow' });
    });
    const unwatchActivate = activateListingFx.doneData.watch(() => {
      notifications.show({ title: t('notifications.done'), message: t('notifications.activated'), color: 'green' });
    });
    const unwatchDelete = deleteListingFx.doneData.watch(() => {
      notifications.show({ title: t('notifications.done'), message: t('notifications.deleted'), color: 'green' });
      setDeleteModalOpen(false);
      setListingToDelete(null);
    });
    return () => { unwatchPause(); unwatchActivate(); unwatchDelete(); };
  }, [t]);

  const propertyTypeLabel = (type: string) => {
    const map: Record<string, string> = {
      apartment: t('propertyTypes.apartment'),
      house: t('propertyTypes.house'),
      commercial: t('propertyTypes.commercial'),
      land: t('propertyTypes.land'),
    };
    return map[type] || type;
  };

  const getListingSource = (sourceType?: string | null): 'platform' | 'olx' => {
    if (sourceType?.toUpperCase() === 'CLAIMED') return 'olx';
    return 'platform';
  };

  const unifiedCards = useMemo((): UnifiedCard[] => {
    const cards: UnifiedCard[] = [];

    // Platform listings
    for (const l of listings) {
      const source = getListingSource(l.source_type);
      if (filter !== 'all' && filter !== source) continue;
      cards.push({
        id: l.id,
        source,
        price: l.price,
        currency: l.currency,
        title:
          l.title ||
          `${l.rooms ? `${l.rooms}-${t('listings.rooms')} ` : ''}${propertyTypeLabel(l.property_type)}${l.district ? ` ${t('listings.inDistrict', { district: translateDistrict(l.district, t) })}` : ''}`,
        imageUrl: l.primary_image_url,
        rooms: l.rooms,
        area: l.area,
        district: l.district,
        status: l.status,
        views_count: l.views_count,
        contacts_count: l.contacts_count,
      });
    }

    if (filter === 'all' || filter === 'olx') {
      for (const l of olxListings) {
        const img = l.images && l.images.length > 0 ? l.images[0] : null;
        cards.push({
          id: `olx-${l.id}`,
          rawId: l.id,
          source: 'olx',
          price: l.price,
          currency: l.currency,
          title: l.description ? l.description.substring(0, 80) : `${l.property_type} — ${l.listing_type}`,
          imageUrl: typeof img === 'string' ? img : null,
          rooms: l.rooms,
          area: l.area_sqm,
          district: l.district,
          externalUrl: l.url,
          postedDate: l.posted_date,
        });
      }
    }

    if (filter === 'all' || filter === 'telegram') {
      for (const l of telegramListings) {
        const img = l.images && l.images.length > 0 ? l.images[0] : null;
        cards.push({
          id: `tg-${l.id}`,
          source: 'telegram',
          price: l.price,
          currency: l.currency,
          title: l.description ? l.description.substring(0, 80) : `${l.property_type} — ${l.listing_type}`,
          imageUrl: typeof img === 'string' ? img : null,
          rooms: l.rooms,
          area: l.area_sqm,
          district: l.district,
          sourceChannel: l.source_channel,
        });
      }
    }

    return cards;
  }, [listings, olxListings, telegramListings, filter, t]);

  const handleDeleteClick = (listingId: string) => {
    setListingToDelete(listingId);
    setDeleteModalOpen(true);
  };

  const confirmDelete = () => {
    if (listingToDelete) deleteListing(listingToDelete);
  };

  const [claimingId, setClaimingId] = useState<string | null>(null);

  const handleClaimOlx = async (olxId: string) => {
    if (claimingId) return;
    setClaimingId(olxId);
    try {
      const listing = await claimOlxListing(olxId);
      setOlxListings((prev) => prev.filter((l) => l.id !== olxId));
      setOlxTotal((prev) => Math.max(0, prev - 1));
      notifications.show({
        title: t('notifications.done'),
        message: t('listings.claimSuccess'),
        color: 'green',
      });
      navigate(`/edit/${listing.id}`);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        notifications.show({
          title: t('listings.alreadyClaimed'),
          message: t('listings.alreadyClaimedMsg'),
          color: 'yellow',
        });
        fetchSellerOLXListings({ page: 1, per_page: 100 })
          .then((olx) => { setOlxListings(olx.items); setOlxTotal(olx.total); })
          .catch(() => { });
        fetchSellerListings({});
      } else if (status === 429) {
        notifications.show({
          title: t('listings.claimLimitTitle'),
          message: t('listings.claimLimitMsg'),
          color: 'red',
        });
      } else {
        notifications.show({
          title: t('notifications.error'),
          message: t('listings.claimError'),
          color: 'red',
        });
      }
    } finally {
      setClaimingId(null);
    }
  };

  const allLoading = isLoading && isCrawledLoading;
  const platformCount = listings.filter((l) => getListingSource(l.source_type) === 'platform').length;
  const claimedOlxCount = listings.filter((l) => l.source_type?.toUpperCase() === 'CLAIMED').length;
  const totalCount = listings.length + olxTotal + telegramTotal;

  const filters = [
    { label: t('listings.all'), value: 'all', count: totalCount },
    { label: t('listings.platform'), value: 'platform', count: platformCount },
    { label: 'OLX', value: 'olx', count: olxTotal + claimedOlxCount },
    { label: 'Telegram', value: 'telegram', count: telegramTotal },
  ];

  const getPropertyInfo = (card: UnifiedCard): string => {
    const parts: string[] = [];
    if (card.rooms) parts.push(`${card.rooms} ${t('listings.rooms')}`);
    if (card.area) parts.push(`${card.area} ${t('listings.sqm')}`);
    if (card.district) parts.push(translateDistrict(card.district, t));
    return parts.join(' · ');
  };

  return (
    <InnerPage
      title={t('listings.myListings')}
      actions={
        <Button
          leftSection={<IconPlus size={16} stroke={2} />}
          radius="xl"
          size="sm"
          style={{
            background: '#228be6',
            border: 'none',
            boxShadow: shadows.accent,
            padding: '0 12px',
            height: 32,
          }}
          onClick={() => navigate('/seller/create')}
        >
          {t('listings.add', 'New')}
        </Button>
      }
      noPadding
    >
      <Container px="sm" py="md">
      <Stack gap={16}>

        {/* ── Modern Compact Header ── */}
        <Box style={{ animation: 'fade-in 0.4s ease-out' }}>
          {/* ── Pill-style filter chips inside a subtle card ── */}
          <Card radius={radii.md} p={4} style={{ background: surface.card, border: '1px solid #f1f5f9', boxShadow: shadows.sm }}>
            <PillTabs tabs={filters} activeValue={filter} onChange={setFilter} />
          </Card>
        </Box>

        {/* ── Loading skeletons ── */}
        {(isLoading || isCrawledLoading) && unifiedCards.length === 0 && (
          <Stack gap="sm" style={{ animation: 'fade-in-up 0.4s ease-out 0.1s both' }}>
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} height={100} radius={12} />
            ))}
          </Stack>
        )}

        {/* ── Empty state ── */}
        {!allLoading && unifiedCards.length === 0 && (
          <Box style={{ animation: 'fade-in-up 0.4s ease-out 0.1s both', marginTop: 32 }}>
            <EmptyState
              icon={IconBuilding}
              title={filter === 'all' ? t('listings.emptyAll') : t('listings.emptySource')}
              description={t('listings.emptyDescription')}
              actionLabel={t('listings.createListing')}
              onAction={() => navigate('/seller/create')}
            />
          </Box>
        )}

        {/* ── Listing cards ── */}
        <Stack gap="xs">
          {unifiedCards.map((card, index) => {
            const isEditable = !!card.status;
            const isCrawled = !isEditable;
            const borderLeftColor = card.status ? statusColors[card.status] : undefined;
            const propertyInfo = getPropertyInfo(card);

            const cardContent = (
              <Card
                radius={radii.md}
                p="xs"
                style={{
                  boxShadow: shadows.sm,
                  border: isCrawled ? '1px dashed #cbd5e1' : '1px solid #f1f5f9',
                  borderLeft: borderLeftColor ? `4px solid ${borderLeftColor}` : '1px solid #f1f5f9',
                  backgroundColor: surface.card,
                  transition: 'transform 0.2s ease, box-shadow 0.2s ease',
                  cursor: 'pointer',
                  animation: `fade-in-up 0.4s ease-out ${0.05 + (index * 0.05)}s both`
                }}
              >
                <Group wrap="nowrap" gap="sm" align="flex-start">
                  <Box style={{ width: 80, height: 80, flexShrink: 0, borderRadius: radii.sm, overflow: 'hidden' }}>
                    <ListingImageThumbnail src={card.imageUrl} />
                  </Box>

                  <Box style={{ flex: 1, minWidth: 0 }}>
                    <Group justify="space-between" wrap="nowrap" align="flex-start" gap={4} mb={2}>
                      <Text size="16px" fw={800} truncate c="dark.9" style={{ fontFamily: 'Outfit, sans-serif' }}>
                        {formatPrice(card.price, card.currency)}
                      </Text>
                      {isEditable && (
                        <Menu position="bottom-end">
                          <Menu.Target>
                            <ActionIcon
                              variant="transparent"
                              radius="xl"
                              size="sm"
                              color="dark.4"
                              onClick={(e) => { e.stopPropagation(); e.preventDefault(); }}
                            >
                              <IconDotsVertical size={16} />
                            </ActionIcon>
                          </Menu.Target>
                          <Menu.Dropdown>
                            <Menu.Item
                              leftSection={<IconEdit size={14} />}
                              onClick={(e) => { e.stopPropagation(); navigate(`/seller/edit/${card.id}`); }}
                            >
                              {t('listings.edit')}
                            </Menu.Item>
                            {card.status === 'active' ? (
                              <Menu.Item
                                leftSection={<IconPlayerPause size={14} />}
                                onClick={(e) => { e.stopPropagation(); pauseListing(card.id); }}
                              >
                                {t('listings.pause')}
                              </Menu.Item>
                            ) : card.status === 'paused' ? (
                              <Menu.Item
                                leftSection={<IconPlayerPlay size={14} />}
                                onClick={(e) => { e.stopPropagation(); activateListing(card.id); }}
                              >
                                {t('listings.activate')}
                              </Menu.Item>
                            ) : null}
                            <Menu.Divider />
                            <Menu.Item
                              leftSection={<IconTrash size={14} />}
                              color="red"
                              onClick={(e) => { e.stopPropagation(); handleDeleteClick(card.id); }}
                            >
                              {t('listings.delete')}
                            </Menu.Item>
                          </Menu.Dropdown>
                        </Menu>
                      )}
                      {card.source === 'olx' && card.rawId && (
                        <Menu position="bottom-end">
                          <Menu.Target>
                            <ActionIcon
                              variant="transparent"
                              radius="xl"
                              size="sm"
                              color="dark.4"
                              onClick={(e) => { e.stopPropagation(); e.preventDefault(); }}
                            >
                              <IconDotsVertical size={16} />
                            </ActionIcon>
                          </Menu.Target>
                          <Menu.Dropdown>
                            <Menu.Item
                              leftSection={<IconEdit size={14} />}
                              onClick={(e) => { e.stopPropagation(); handleClaimOlx(card.rawId!); }}
                            >
                              {t('listings.edit')}
                            </Menu.Item>
                            {card.externalUrl && (
                              <Menu.Item
                                leftSection={<IconExternalLink size={14} />}
                                component="a"
                                href={card.externalUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                {t('listings.viewOnOlx')}
                              </Menu.Item>
                            )}
                          </Menu.Dropdown>
                        </Menu>
                      )}
                      {card.source === 'telegram' && card.externalUrl && (
                        <ActionIcon variant="transparent" component="div" size="sm">
                          <IconExternalLink size={16} color="#94a3b8" />
                        </ActionIcon>
                      )}
                    </Group>

                    <Text size="12px" c="dark.6" lh={1.3} lineClamp={2} mb={6} fw={500}>
                      {card.title}
                    </Text>

                    {propertyInfo && (
                      <Text size="10px" fw={700} c="dimmed" truncate mb={6} tt="uppercase" style={{ letterSpacing: '0.2px' }}>
                        {propertyInfo}
                      </Text>
                    )}

                    <Group gap={6}>
                      <Badge variant="light" size="xs" color={sourceColors[card.source]} radius="sm" style={{ fontWeight: 800 }}>
                        {sourceLabels[card.source]}
                      </Badge>
                      {card.status && (
                        <Badge variant="dot" size="xs" color={borderLeftColor?.replace('#', '') || 'gray'} radius="sm" style={{ border: 'none', background: '#f1f5f9', fontWeight: 800 }}>
                          {statusLabels[card.status] || card.status}
                        </Badge>
                      )}
                      <Group gap={4} wrap="nowrap" ml="auto">
                        {card.views_count !== undefined && (
                          <Group gap={2} wrap="nowrap" bg="#f1f5f9" px={6} py={2} style={{ borderRadius: 6 }}>
                            <IconEye size={12} color="#64748b" />
                            <Text size="10px" c="#334155" fw={700}>{card.views_count}</Text>
                          </Group>
                        )}
                        {card.contacts_count !== undefined && card.contacts_count > 0 && (
                          <Group gap={2} wrap="nowrap" ml={2} bg="#f1f5f9" px={6} py={2} style={{ borderRadius: 6 }}>
                            <IconPhone size={12} color="#64748b" />
                            <Text size="10px" c="#334155" fw={700}>{card.contacts_count}</Text>
                          </Group>
                        )}
                      </Group>
                    </Group>
                  </Box>
                </Group>
              </Card>
            );

            if (card.source === 'telegram' && card.externalUrl) {
              return (
                <Box component="a" key={card.id} href={card.externalUrl} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none' }}>
                  {cardContent}
                </Box>
              );
            }

            return <Box key={card.id} onClick={() => { if (isEditable) navigate(`/seller/edit/${card.id}`) }}>{cardContent}</Box>;
          })}
        </Stack>
      </Stack>

      <style>{`
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes fade-in-up {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <Modal opened={deleteModalOpen} onClose={() => setDeleteModalOpen(false)} title={<Text fw={700} size="lg" style={{ fontFamily: 'Outfit, sans-serif' }}>{t('listings.deleteTitle', 'Delete Listing')}</Text>} centered radius={radii.lg} overlayProps={{ blur: 4, backgroundOpacity: 0.4 }} padding="md">
        <Stack gap="md">
          <Text size="sm" c="dimmed" lh={1.4}>
            {t('listings.deleteConfirm', 'Are you sure you want to permanently delete this listing?')}
          </Text>
          <Group justify="flex-end" gap="sm">
            <Button variant="default" onClick={() => setDeleteModalOpen(false)} radius="xl" size="sm" style={{ border: 'none', background: surface.muted, color: '#475569' }}>
              {t('listings.cancel')}
            </Button>
            <Button color="red" onClick={confirmDelete} radius="xl" size="sm">
              {t('listings.delete')}
            </Button>
          </Group>
        </Stack>
      </Modal>
      </Container>
    </InnerPage>
  );
}

export const SellerListings = {
  route: '/seller/listings',
  Page,
};
