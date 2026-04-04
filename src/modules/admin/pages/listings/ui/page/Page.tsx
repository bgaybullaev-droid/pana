import { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useUnit } from 'effector-react';
import {
  Text,
  Group,
  Stack,
  TextInput,
  Pagination,
  UnstyledButton,
  Image,
  Box,
} from '@mantine/core';
import {
  IconSearch,
  IconChevronRight,
  IconPhoto,
  IconBuildingSkyscraper,
} from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import {
  $listings,
  $listingsPagination,
  $isLoadingListings,
  fetchListings,
} from '@modules/admin/shared/state';
import { formatPrice } from '@app/styles/theme';
import { translateDistrict } from '@shared/lib/regions';
import '@modules/admin/shared/ui/admin.css';

/* ---------- Helpers ---------- */
function getBadgeClass(status: string) {
  switch (status) {
    case 'pending': return 'admin-badge admin-badge--pending';
    case 'approved': return 'admin-badge admin-badge--approved';
    case 'rejected': return 'admin-badge admin-badge--rejected';
    default: return 'admin-badge';
  }
}

function getSourcePill(source: string) {
  const colors: Record<string, { bg: string; color: string }> = {
    manual: { bg: 'rgba(99, 102, 241, 0.1)', color: '#4f46e5' },
    claimed: { bg: 'rgba(6, 182, 212, 0.1)', color: '#0891b2' },
    parsed: { bg: 'rgba(168, 85, 247, 0.1)', color: '#7c3aed' },
  };
  const c = colors[source] || { bg: 'rgba(148, 163, 184, 0.1)', color: '#64748b' };
  return (
    <Box
      component="span"
      style={{
        background: c.bg, color: c.color,
        fontSize: 10, fontWeight: 700, padding: '2px 8px',
        borderRadius: 6, textTransform: 'uppercase', letterSpacing: '0.3px',
      }}
    >
      {source}
    </Box>
  );
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

/* ---------- Content-Aware Skeleton ---------- */
function ListingCardSkeleton({ index }: { index: number }) {
  return (
    <Box className={`admin-skeleton-card admin-stagger-${index + 1}`}>
      <Group wrap="nowrap" gap={12} align="flex-start">
        <Box className="admin-skeleton-circle" style={{ width: 72, height: 72, borderRadius: 12, flexShrink: 0 }} />
        <Stack gap={6} style={{ flex: 1 }}>
          <Group gap={8} justify="space-between">
            <Box className="admin-skeleton-line" style={{ width: '65%' }} />
            <Box className="admin-skeleton-badge" style={{ width: 20, height: 20, borderRadius: 4 }} />
          </Group>
          <Box className="admin-skeleton-line" style={{ width: '35%', height: 14 }} />
          <Box className="admin-skeleton-line" style={{ width: '50%', height: 10, opacity: 0.5 }} />
          <Group gap={6}>
            <Box className="admin-skeleton-badge" style={{ width: 52 }} />
            <Box className="admin-skeleton-badge" style={{ width: 44 }} />
          </Group>
        </Stack>
      </Group>
    </Box>
  );
}

/* ---------- Main Page ---------- */
function Page() {
  const navigate = useNavigate();
  const { t } = useTranslation('admin');
  const [searchParams, setSearchParams] = useSearchParams();
  const [listings, pagination, isLoading] = useUnit([
    $listings,
    $listingsPagination,
    $isLoadingListings,
  ]);

  const [search, setSearch] = useState(searchParams.get('q') || '');
  const [moderationStatus, setModerationStatus] = useState<string | null>(
    searchParams.get('moderation_status')
  );
  const [sourceType, setSourceType] = useState<string | null>(
    searchParams.get('source_type')
  );
  const [page, setPage] = useState(
    parseInt(searchParams.get('page') || '1', 10)
  );
  const lastParamsRef = useRef<string | null>(null);

  useEffect(() => {
    const params: Record<string, string> = {};
    if (search) params.q = search;
    if (moderationStatus) params.moderation_status = moderationStatus;
    if (sourceType) params.source_type = sourceType;
    if (page > 1) params.page = page.toString();

    const paramsKey = JSON.stringify({ search, moderationStatus, sourceType, page });
    if (lastParamsRef.current === paramsKey) return;
    lastParamsRef.current = paramsKey;

    setSearchParams(params);

    fetchListings({
      page,
      moderation_status: moderationStatus || undefined,
      source_type: sourceType || undefined,
    });
  }, [search, moderationStatus, sourceType, page, setSearchParams]);

  const statusOptions: ChipOption[] = [
    { value: null, label: t('common.all') },
    { value: 'pending', label: t('common.pending'), colorClass: 'admin-chip--pending' },
    { value: 'approved', label: t('common.approved'), colorClass: 'admin-chip--approved' },
    { value: 'rejected', label: t('common.rejected'), colorClass: 'admin-chip--rejected' },
  ];

  const sourceOptions: ChipOption[] = [
    { value: null, label: t('common.allSources') },
    { value: 'manual', label: t('listings.manual'), colorClass: 'admin-chip--manual' },
    { value: 'claimed', label: t('listings.claimed'), colorClass: 'admin-chip--claimed' },
    { value: 'parsed', label: t('listings.parsed'), colorClass: 'admin-chip--parsed' },
  ];

  return (
    <Box className="admin-page-enter" py="md" px="md">
      {/* Page Title */}
      <Group justify="space-between" align="center" mb="md">
        <Box>
          <Text size="xl" fw={800} style={{ color: '#1e293b' }}>{t('listings.title')}</Text>
          <Text size="xs" c="dimmed" fw={500}>{t('listings.subtitle')}</Text>
        </Box>
        {pagination.total > 0 && (
          <Box style={{ background: 'rgba(6, 182, 212, 0.1)', borderRadius: 10, padding: '4px 12px' }}>
            <Text size="xs" fw={700} style={{ color: '#0891b2' }}>{pagination.total}</Text>
          </Box>
        )}
      </Group>

      {/* Search */}
      <Box className="admin-filter-bar" style={{ marginBottom: 8 }}>
        <TextInput
          placeholder={t('listings.searchPlaceholder')}
          leftSection={<IconSearch size={16} color="#94a3b8" />}
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          styles={{
            input: { border: '1px solid rgba(0, 0, 0, 0.06)', borderRadius: 12, background: '#f8fafc' },
          }}
        />
      </Box>

      {/* Chip Filters */}
      <Stack gap={8} mb="md">
        <ChipFilter
          options={statusOptions}
          value={moderationStatus}
          onChange={(v) => { setModerationStatus(v); setPage(1); }}
        />
        <ChipFilter
          options={sourceOptions}
          value={sourceType}
          onChange={(v) => { setSourceType(v); setPage(1); }}
        />
      </Stack>

      {/* Results */}
      {isLoading ? (
        <Stack gap={8}>
          {[0, 1, 2, 3, 4].map((i) => (
            <ListingCardSkeleton key={i} index={i} />
          ))}
        </Stack>
      ) : listings.length === 0 ? (
        <Box className="admin-empty-state">
          <Box className="admin-empty-state-icon">
            <IconBuildingSkyscraper size={36} color="#94a3b8" />
          </Box>
          <Text fw={600} size="md" style={{ color: '#475569' }}>{t('listings.noListingsFound')}</Text>
          <Text size="sm" c="dimmed" mt={4}>{t('common.tryAdjustingFilters')}</Text>
        </Box>
      ) : (
        <Stack gap={8}>
          {listings.map((listing, index) => (
            <UnstyledButton
              key={listing.id}
              onClick={() => navigate(`/admin/listings/${listing.id}`)}
              style={{ width: '100%' }}
            >
              <Box className={`admin-list-card admin-list-card--${listing.moderation_status} admin-stagger-${Math.min(index + 1, 10)}`}>
                <Group wrap="nowrap" gap={12} align="flex-start">
                  {/* Image Thumbnail */}
                  {listing.primary_image_url ? (
                    <Image
                      src={listing.primary_image_url}
                      width={72}
                      height={72}
                      radius={12}
                      fit="cover"
                      style={{ flexShrink: 0 }}
                    />
                  ) : (
                    <Box style={{
                      width: 72, height: 72, background: 'linear-gradient(135deg, #f1f5f9, #e2e8f0)',
                      borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                    }}>
                      <IconPhoto size={28} color="#cbd5e1" />
                    </Box>
                  )}

                  {/* Content */}
                  <Box style={{ flex: 1, minWidth: 0 }}>
                    <Group justify="space-between" wrap="nowrap" mb={4}>
                      <Text fw={600} size="sm" lineClamp={1} style={{ color: '#1e293b', flex: 1 }}>
                        {listing.title || `${listing.property_type} for ${listing.type}`}
                      </Text>
                      <IconChevronRight size={16} color="#cbd5e1" style={{ flexShrink: 0 }} />
                    </Group>

                    <Text size="sm" fw={700} style={{ color: '#4f46e5' }} mb={4}>
                      {formatPrice(listing.price, listing.currency)}
                    </Text>

                    <Group gap={6} wrap="nowrap" mb={6}>
                      {listing.district && (
                        <Text size="xs" style={{ color: '#94a3b8' }} lineClamp={1}>
                          {translateDistrict(listing.district, t)}
                        </Text>
                      )}
                      {listing.seller_name && (
                        <>
                          <Text size="xs" style={{ color: '#e2e8f0' }}>|</Text>
                          <Text size="xs" style={{ color: '#94a3b8' }} lineClamp={1}>
                            {listing.seller_name}
                          </Text>
                        </>
                      )}
                    </Group>

                    <Group gap={6}>
                      <Box className={getBadgeClass(listing.moderation_status)}>
                        {listing.moderation_status}
                      </Box>
                      {getSourcePill(listing.source_type)}
                    </Group>
                  </Box>
                </Group>
              </Box>
            </UnstyledButton>
          ))}
        </Stack>
      )}

      {/* Pagination */}
      {pagination.totalPages > 1 && (
        <Group justify="center" mt="xl">
          <Pagination total={pagination.totalPages} value={page} onChange={setPage} radius="xl" size="sm"
            styles={{ control: { border: 'none', fontWeight: 600 } }}
          />
        </Group>
      )}

      {listings.length > 0 && (
        <Text size="xs" c="dimmed" ta="center" mt="sm" fw={500}>
          {t('listings.showing', { count: listings.length, total: pagination.total })}
        </Text>
      )}
    </Box>
  );
}

export const AdminListings = {
  route: '/admin/listings',
  Page,
};
