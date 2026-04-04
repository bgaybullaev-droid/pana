import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUnit } from 'effector-react';
import { formatTimeAgo } from '@shared/lib/date';
import {
  Text,
  Group,
  Stack,
  Pagination,
  UnstyledButton,
  Image,
  Box,
} from '@mantine/core';
import {
  IconWorldSearch,
  IconBrandTelegram,
  IconPhoto,
  IconBed,
  IconRuler2,
  IconStairs,
  IconChevronRight,
  IconEye,
} from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import type { OLXListing, TelegramListing } from '@shared/api/types';
import {
  pageOpened,
  sourceChanged,
  pageChanged,
  propertyTypeChanged,
  resetCrawledState,
  $crawledStats,
  $activeSource,
  $crawledPage,
  $propertyType,
  $olxListings,
  $telegramListings,
  $olxTotal,
  $telegramTotal,
  $olxTotalPages,
  $telegramTotalPages,
  $isLoadingCrawled,
  $isLoadingCrawledStats,
} from '../../model';
import type { CrawledSource } from '../../model';
import { formatPrice } from '@app/styles/theme';
import { translateDistrict } from '@shared/lib/regions';
import '@modules/admin/shared/ui/admin.css';

/* ---------- Helpers ---------- */
function getFirstImage(images: string[] | null): string | null {
  if (!images || images.length === 0) return null;
  const first = images[0];
  if (typeof first === 'string') return first;
  if (typeof first === 'object' && first !== null && 'url' in first) {
    return (first as { url: string }).url;
  }
  return null;
}

function getConfidenceColor(confidence: number | null): { color: string; bg: string; label: string } {
  if (confidence === null) return { color: '#94a3b8', bg: 'rgba(148, 163, 184, 0.1)', label: 'N/A' };
  const pct = Math.round(confidence * 100);
  if (pct >= 80) return { color: '#059669', bg: 'rgba(16, 185, 129, 0.1)', label: `${pct}%` };
  if (pct >= 50) return { color: '#d97706', bg: 'rgba(245, 158, 11, 0.1)', label: `${pct}%` };
  return { color: '#dc2626', bg: 'rgba(239, 68, 68, 0.1)', label: `${pct}%` };
}

/* ---------- Chip Filter ---------- */
interface ChipOption {
  value: string | null;
  label: string;
  colorClass?: string;
}

function ChipFilter({
  options,
  value,
  onChange,
}: {
  options: ChipOption[];
  value: string | null;
  onChange: (v: string | null) => void;
}) {
  return (
    <Box className="admin-chips-scroll">
      {options.map((opt) => (
        <Box
          key={opt.value ?? '__all'}
          className={`admin-chip ${opt.colorClass || ''} ${value === opt.value ? 'admin-chip--active' : ''}`}
          onClick={() => onChange(opt.value === value ? null : opt.value)}
        >
          {opt.label}
        </Box>
      ))}
    </Box>
  );
}

/* ---------- Stats Cards ---------- */
function CrawledStatsCards({ olxCount, tgCount }: { olxCount: number; tgCount: number }) {
  const total = olxCount + tgCount;
  const olxPct = total > 0 ? Math.round((olxCount / total) * 100) : 0;
  const tgPct = total > 0 ? Math.round((tgCount / total) * 100) : 0;

  return (
    <Group grow gap={10} mb="md">
      <Box className="admin-crawled-stat-card admin-crawled-stat-card--olx">
        <Box className="admin-crawled-stat-icon">
          <IconWorldSearch size={20} color="white" />
        </Box>
        <Text fw={800} style={{ fontSize: 28, lineHeight: 1, color: '#1e293b' }}>{olxCount}</Text>
        <Text size="xs" fw={600} style={{ color: '#64748b' }}>OLX.uz</Text>
        <Box className="admin-crawled-stat-bar">
          <Box className="admin-crawled-stat-bar-fill admin-crawled-stat-bar-fill--olx" style={{ width: `${olxPct}%` }} />
        </Box>
      </Box>
      <Box className="admin-crawled-stat-card admin-crawled-stat-card--telegram">
        <Box className="admin-crawled-stat-icon admin-crawled-stat-icon--telegram">
          <IconBrandTelegram size={20} color="white" />
        </Box>
        <Text fw={800} style={{ fontSize: 28, lineHeight: 1, color: '#1e293b' }}>{tgCount}</Text>
        <Text size="xs" fw={600} style={{ color: '#64748b' }}>Telegram</Text>
        <Box className="admin-crawled-stat-bar">
          <Box className="admin-crawled-stat-bar-fill admin-crawled-stat-bar-fill--telegram" style={{ width: `${tgPct}%` }} />
        </Box>
      </Box>
    </Group>
  );
}

/* ---------- Content-Aware Skeleton ---------- */
function CrawledCardSkeleton({ index }: { index: number }) {
  return (
    <Box className={`admin-skeleton-card admin-stagger-${index + 1}`}>
      <Group gap={6} mb={8}>
        <Box className="admin-skeleton-badge" style={{ width: 60 }} />
        <Box className="admin-skeleton-badge" style={{ width: 36 }} />
      </Group>
      <Group wrap="nowrap" gap={12} align="flex-start">
        <Box className="admin-skeleton-circle" style={{ width: 72, height: 72, borderRadius: 12, flexShrink: 0 }} />
        <Stack gap={6} style={{ flex: 1 }}>
          <Box className="admin-skeleton-line" style={{ width: '40%', height: 14 }} />
          <Box className="admin-skeleton-line" style={{ width: '70%' }} />
          <Box className="admin-skeleton-line" style={{ width: '50%', height: 10, opacity: 0.5 }} />
          <Group gap={6}>
            <Box className="admin-skeleton-badge" style={{ width: 40 }} />
            <Box className="admin-skeleton-badge" style={{ width: 48 }} />
            <Box className="admin-skeleton-badge" style={{ width: 36 }} />
          </Group>
        </Stack>
      </Group>
    </Box>
  );
}

/* ---------- OLX Card ---------- */
function OLXCard({ listing }: { listing: OLXListing }) {
  const navigate = useNavigate();
  const { t } = useTranslation('admin');
  const imageUrl = getFirstImage(listing.images);
  const conf = getConfidenceColor(listing.confidence);
  const imageCount = listing.images?.length || 0;

  return (
    <UnstyledButton onClick={() => navigate(`/admin/crawled/olx/${listing.id}`)} style={{ width: '100%' }}>
      <Box className="admin-crawled-card admin-crawled-card--olx">
        {/* Source Header */}
        <Group justify="space-between" mb={8}>
          <Group gap={6}>
            <Box className="admin-source-badge admin-source-badge--olx">
              <IconWorldSearch size={12} />
              OLX.uz
            </Box>
            <Box className="admin-confidence-badge" style={{ background: conf.bg, color: conf.color }}>
              {conf.label}
            </Box>
          </Group>
          <Text size="xs" style={{ color: '#94a3b8' }}>{formatTimeAgo(listing.crawled_at)}</Text>
        </Group>

        <Group wrap="nowrap" gap={12} align="flex-start">
          {/* Thumbnail */}
          <Box style={{ position: 'relative', flexShrink: 0 }}>
            {imageUrl ? (
              <Image src={imageUrl} width={72} height={72} radius={12} fit="cover" />
            ) : (
              <Box style={{
                width: 72, height: 72, background: 'linear-gradient(135deg, #f1f5f9, #e2e8f0)',
                borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <IconPhoto size={24} color="#cbd5e1" />
              </Box>
            )}
            {imageCount > 1 && (
              <Box className="admin-image-count-badge">
                <IconPhoto size={9} />
                {imageCount}
              </Box>
            )}
          </Box>

          {/* Content */}
          <Box style={{ flex: 1, minWidth: 0 }}>
            <Text size="sm" fw={700} style={{ color: '#4f46e5' }} mb={2}>
              {formatPrice(listing.price, listing.currency)}
            </Text>
            <Text size="sm" fw={600} lineClamp={1} style={{ color: '#1e293b' }} mb={2}>
              {listing.description
                ? listing.description.substring(0, 60)
                : `${listing.property_type} — ${listing.listing_type}`}
            </Text>
            {listing.district && (
              <Text size="xs" style={{ color: '#94a3b8' }} mb={4} lineClamp={1}>{translateDistrict(listing.district, t)}</Text>
            )}

            {/* Quick stats */}
            <Group gap={6} mb={4}>
              {listing.rooms && (
                <Box className="admin-crawled-quick-stat">
                  <IconBed size={11} />
                  {listing.rooms}
                </Box>
              )}
              {listing.area_sqm && (
                <Box className="admin-crawled-quick-stat">
                  <IconRuler2 size={11} />
                  {listing.area_sqm}m²
                </Box>
              )}
              {listing.floor && (
                <Box className="admin-crawled-quick-stat">
                  <IconStairs size={11} />
                  {listing.floor}{listing.total_floors ? `/${listing.total_floors}` : ''}
                </Box>
              )}
            </Group>

            {/* OLX-specific info */}
            <Group gap={6}>
              {listing.seller_type && (
                <Text size="xs" style={{ color: '#94a3b8' }}>{listing.seller_type}</Text>
              )}
              {listing.condition && (
                <Box className="admin-amenity-chip">{listing.condition}</Box>
              )}
              {listing.views_count != null && listing.views_count > 0 && (
                <Group gap={2}>
                  <IconEye size={11} color="#94a3b8" />
                  <Text size="xs" style={{ color: '#94a3b8' }}>{listing.views_count}</Text>
                </Group>
              )}
            </Group>
          </Box>

          <IconChevronRight size={16} color="#cbd5e1" style={{ flexShrink: 0, marginTop: 4 }} />
        </Group>
      </Box>
    </UnstyledButton>
  );
}

/* ---------- Telegram Card ---------- */
function TelegramCard({ listing }: { listing: TelegramListing }) {
  const navigate = useNavigate();
  const { t } = useTranslation('admin');
  const imageUrl = getFirstImage(listing.images);
  const conf = getConfidenceColor(listing.confidence);
  const imageCount = listing.images?.length || 0;

  return (
    <UnstyledButton onClick={() => navigate(`/admin/crawled/telegram/${listing.id}`)} style={{ width: '100%' }}>
      <Box className="admin-crawled-card admin-crawled-card--telegram">
        {/* Source Header */}
        <Group justify="space-between" mb={8}>
          <Group gap={6}>
            <Box className="admin-source-badge admin-source-badge--telegram">
              <IconBrandTelegram size={12} />
              Telegram
            </Box>
            <Box className="admin-confidence-badge" style={{ background: conf.bg, color: conf.color }}>
              {conf.label}
            </Box>
          </Group>
          <Text size="xs" style={{ color: '#94a3b8' }}>{formatTimeAgo(listing.created_at)}</Text>
        </Group>

        <Group wrap="nowrap" gap={12} align="flex-start">
          {/* Thumbnail */}
          <Box style={{ position: 'relative', flexShrink: 0 }}>
            {imageUrl ? (
              <Image src={imageUrl} width={72} height={72} radius={12} fit="cover" />
            ) : (
              <Box style={{
                width: 72, height: 72, background: 'linear-gradient(135deg, #f1f5f9, #e2e8f0)',
                borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <IconPhoto size={24} color="#cbd5e1" />
              </Box>
            )}
            {imageCount > 1 && (
              <Box className="admin-image-count-badge">
                <IconPhoto size={9} />
                {imageCount}
              </Box>
            )}
          </Box>

          {/* Content */}
          <Box style={{ flex: 1, minWidth: 0 }}>
            <Text size="sm" fw={700} style={{ color: '#4f46e5' }} mb={2}>
              {formatPrice(listing.price, listing.currency)}
            </Text>
            <Text size="sm" fw={600} lineClamp={1} style={{ color: '#1e293b' }} mb={2}>
              {listing.description
                ? listing.description.substring(0, 60)
                : `${listing.property_type} — ${listing.listing_type}`}
            </Text>
            {listing.district && (
              <Text size="xs" style={{ color: '#94a3b8' }} mb={4} lineClamp={1}>{translateDistrict(listing.district, t)}</Text>
            )}

            {/* Quick stats */}
            <Group gap={6} mb={4}>
              {listing.rooms && (
                <Box className="admin-crawled-quick-stat">
                  <IconBed size={11} />
                  {listing.rooms}
                </Box>
              )}
              {listing.area_sqm && (
                <Box className="admin-crawled-quick-stat">
                  <IconRuler2 size={11} />
                  {listing.area_sqm}m²
                </Box>
              )}
              {listing.floor && (
                <Box className="admin-crawled-quick-stat">
                  <IconStairs size={11} />
                  {listing.floor}{listing.total_floors ? `/${listing.total_floors}` : ''}
                </Box>
              )}
            </Group>

            {/* Telegram-specific info */}
            {listing.source_channel && (
              <Text size="xs" style={{ color: '#0ea5e9' }} lineClamp={1}>
                {listing.source_channel}
              </Text>
            )}
          </Box>

          <IconChevronRight size={16} color="#cbd5e1" style={{ flexShrink: 0, marginTop: 4 }} />
        </Group>
      </Box>
    </UnstyledButton>
  );
}

/* ---------- Main Page ---------- */
function Page() {
  const { t } = useTranslation('admin');
  const [
    stats, activeSource, page, propertyType,
    olxListings, telegramListings,
    olxTotal, telegramTotal,
    olxTotalPages, telegramTotalPages,
    isLoading, isStatsLoading,
  ] = useUnit([
    $crawledStats, $activeSource, $crawledPage, $propertyType,
    $olxListings, $telegramListings,
    $olxTotal, $telegramTotal,
    $olxTotalPages, $telegramTotalPages,
    $isLoadingCrawled, $isLoadingCrawledStats,
  ]);

  const initializedRef = useRef(false);

  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;
    pageOpened();
    return () => { resetCrawledState(); };
  }, []);

  const sourceOptions: ChipOption[] = [
    { value: 'all', label: t('common.allSources') },
    { value: 'olx', label: `OLX ${stats ? `(${stats.olx_count})` : ''}`, colorClass: 'admin-chip--olx-source' },
    { value: 'telegram', label: `Telegram ${stats ? `(${stats.telegram_count})` : ''}`, colorClass: 'admin-chip--telegram-source' },
  ];

  const propertyOptions: ChipOption[] = [
    { value: null, label: t('common.allTypes') },
    { value: 'apartment', label: t('crawled.apartment') },
    { value: 'house', label: t('crawled.house') },
    { value: 'commercial', label: t('crawled.commercial') },
    { value: 'land', label: t('crawled.land') },
  ];

  // Build combined listings with source tag for "all" view
  type TaggedListing =
    | { source: 'olx'; data: OLXListing }
    | { source: 'telegram'; data: TelegramListing };

  let combinedListings: TaggedListing[] = [];
  if (activeSource === 'all') {
    const olxTagged: TaggedListing[] = olxListings.map((l) => ({ source: 'olx' as const, data: l }));
    const tgTagged: TaggedListing[] = telegramListings.map((l) => ({ source: 'telegram' as const, data: l }));
    combinedListings = [...olxTagged, ...tgTagged].sort(
      (a, b) => new Date(b.data.created_at).getTime() - new Date(a.data.created_at).getTime()
    );
  }

  const totalItems = activeSource === 'olx' ? olxTotal : activeSource === 'telegram' ? telegramTotal : olxTotal + telegramTotal;
  const totalPages = activeSource === 'olx' ? olxTotalPages : activeSource === 'telegram' ? telegramTotalPages : Math.max(olxTotalPages, telegramTotalPages);

  const hasListings = activeSource === 'all'
    ? combinedListings.length > 0
    : activeSource === 'olx'
      ? olxListings.length > 0
      : telegramListings.length > 0;

  return (
    <Box className="admin-page-enter" py="md" px="md">
      {/* Page Title */}
      <Group justify="space-between" align="center" mb="md">
        <Box>
          <Text size="xl" fw={800} style={{ color: '#1e293b' }}>{t('crawled.title')}</Text>
          <Text size="xs" c="dimmed" fw={500}>{t('crawled.subtitle')}</Text>
        </Box>
        {totalItems > 0 && (
          <Box style={{ background: 'rgba(168, 85, 247, 0.1)', borderRadius: 10, padding: '4px 12px' }}>
            <Text size="xs" fw={700} style={{ color: '#7c3aed' }}>{totalItems}</Text>
          </Box>
        )}
      </Group>

      {/* Stats Cards */}
      {isStatsLoading ? (
        <Group grow gap={10} mb="md">
          <Box className="admin-skeleton" style={{ height: 110, borderRadius: 16 }} />
          <Box className="admin-skeleton" style={{ height: 110, borderRadius: 16 }} />
        </Group>
      ) : stats ? (
        <CrawledStatsCards olxCount={stats.olx_count} tgCount={stats.telegram_count} />
      ) : null}

      {/* Chip Filters */}
      <Stack gap={8} mb="md">
        <ChipFilter
          options={sourceOptions}
          value={activeSource}
          onChange={(v) => sourceChanged((v || 'all') as CrawledSource)}
        />
        <ChipFilter
          options={propertyOptions}
          value={propertyType}
          onChange={(v) => { propertyTypeChanged(v); pageChanged(1); }}
        />
      </Stack>

      {/* Results */}
      {isLoading ? (
        <Stack gap={8}>
          {[0, 1, 2, 3, 4].map((i) => (
            <CrawledCardSkeleton key={i} index={i} />
          ))}
        </Stack>
      ) : !hasListings ? (
        <Box className="admin-empty-state">
          <Box className="admin-empty-state-icon">
            <IconWorldSearch size={36} color="#94a3b8" />
          </Box>
          <Text fw={600} size="md" style={{ color: '#475569' }}>{t('crawled.noListingsFound')}</Text>
          <Text size="sm" c="dimmed" mt={4}>{t('common.tryAdjustingFilters')}</Text>
        </Box>
      ) : activeSource === 'all' ? (
        <Stack gap={8}>
          {combinedListings.map((item) => (
            item.source === 'olx'
              ? <OLXCard key={`olx-${item.data.id}`} listing={item.data as OLXListing} />
              : <TelegramCard key={`tg-${item.data.id}`} listing={item.data as TelegramListing} />
          ))}
        </Stack>
      ) : activeSource === 'olx' ? (
        <Stack gap={8}>
          {olxListings.map((listing) => (
            <OLXCard key={listing.id} listing={listing} />
          ))}
        </Stack>
      ) : (
        <Stack gap={8}>
          {telegramListings.map((listing) => (
            <TelegramCard key={listing.id} listing={listing} />
          ))}
        </Stack>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <Group justify="center" mt="xl">
          <Pagination total={totalPages} value={page} onChange={pageChanged} radius="xl" size="sm"
            styles={{ control: { border: 'none', fontWeight: 600 } }}
          />
        </Group>
      )}

      {hasListings && (
        <Text size="xs" c="dimmed" ta="center" mt="sm" fw={500}>
          {t('crawled.totalListings', { count: totalItems })}
        </Text>
      )}
    </Box>
  );
}

export const AdminCrawled = {
  route: '/admin/crawled',
  Page,
};
