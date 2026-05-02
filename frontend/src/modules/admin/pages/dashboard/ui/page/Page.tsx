import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUnit } from 'effector-react';
import {
  Text,
  Box,
  Group,
  Stack,
  UnstyledButton,
} from '@mantine/core';
import {
  IconUsers,
  IconBuildingSkyscraper,
  IconClock,
  IconChevronRight,
  IconArrowUpRight,
  IconWorldSearch,
  IconBrandTelegram,
} from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import {
  $dashboardStats,
  $isLoadingDashboard,
  fetchDashboardStats,
} from '@modules/admin/shared/state';
import {
  $crawledStats,
  fetchCrawledStatsFx,
} from '../../../crawled/model';
import '@modules/admin/shared/ui/admin.css';

/* ---------- Animated counter ---------- */
function useAnimatedCount(target: number, duration = 800) {
  const [count, setCount] = useState(0);
  const prevTarget = useRef(0);

  useEffect(() => {
    if (target === prevTarget.current) return;
    prevTarget.current = target;
    const startTime = performance.now();
    function tick(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(target * eased));
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }, [target, duration]);

  return count;
}

/* ---------- Progress Ring ---------- */
interface ProgressRingProps {
  value: number;
  total: number;
  label: string;
  ofTotalText: string;
  color: string;
  glowColor: string;
  delay: number;
  onClick: () => void;
}

function ProgressRing({ value, total, label, ofTotalText, color, glowColor, delay, onClick }: ProgressRingProps) {
  const animatedValue = useAnimatedCount(value);
  const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (circumference * percentage) / 100;

  return (
    <UnstyledButton onClick={onClick} style={{ width: '100%' }}>
      <Box
        className="admin-ring-card"
        style={{ animationDelay: `${delay}ms` }}
      >
        <Box style={{ position: 'relative', width: 96, height: 96, margin: '0 auto' }}>
          <svg className="admin-ring-svg" width={96} height={96} viewBox="0 0 96 96">
            <circle className="admin-ring-track" cx={48} cy={48} r={radius} />
            <circle
              className="admin-ring-fill"
              cx={48}
              cy={48}
              r={radius}
              stroke={color}
              style={{
                '--ring-circumference': circumference,
                '--ring-offset': offset,
                '--ring-delay': `${delay + 200}ms`,
                '--ring-glow': glowColor,
              } as React.CSSProperties}
            />
          </svg>
          <Box className="admin-ring-center">
            <Text fw={800} style={{ fontSize: 22, color: '#1e293b', lineHeight: 1 }}>
              {animatedValue}
            </Text>
            <Text size="xs" fw={600} style={{ color: '#94a3b8', fontSize: 10 }}>
              {percentage}%
            </Text>
          </Box>
        </Box>
        <Text size="xs" fw={700} mt={8} style={{ color: '#475569' }}>
          {label}
        </Text>
        <Text size="xs" style={{ color: '#cbd5e1', fontSize: 10 }}>
          {ofTotalText}
        </Text>
      </Box>
    </UnstyledButton>
  );
}

/* ---------- Pending Card ---------- */
interface PendingCardProps {
  title: string;
  value: number;
  icon: typeof IconClock;
  gradient: string;
  delay: number;
  onClick: () => void;
}

function PendingCard({ title, value, icon: Icon, gradient, delay, onClick }: PendingCardProps) {
  const { t } = useTranslation('admin');
  const animatedValue = useAnimatedCount(value);

  return (
    <UnstyledButton onClick={onClick} style={{ width: '100%' }}>
      <Box className={`admin-stat-card ${gradient}`} style={{ animationDelay: `${delay}ms` }}>
        <Group justify="space-between" align="flex-start">
          <Stack gap={4} style={{ position: 'relative', zIndex: 1 }}>
            <Text size="xs" fw={600} style={{ opacity: 0.85, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
              {title}
            </Text>
            <Text className="stat-value" fw={800} style={{ fontSize: 36, lineHeight: 1, animationDelay: `${delay + 150}ms` }}>
              {animatedValue}
            </Text>
            <Group gap={4} mt={4} style={{ opacity: 0.8 }}>
              <Text size="xs" fw={500}>{t('common.viewAll')}</Text>
              <IconChevronRight size={14} />
            </Group>
          </Stack>
          <Box className="stat-icon" style={{ opacity: 0.25 }}>
            <Icon size={56} strokeWidth={1.5} />
          </Box>
        </Group>
      </Box>
    </UnstyledButton>
  );
}

/* ---------- Crawled Mini Card ---------- */
function CrawledMiniCard({ label, count, icon: Icon, color, iconBg, delay, onClick }: {
  label: string; count: number; icon: typeof IconWorldSearch; color: string; iconBg: string; delay: number; onClick: () => void;
}) {
  const animatedValue = useAnimatedCount(count);

  return (
    <UnstyledButton onClick={onClick} style={{ width: '100%' }}>
      <Box className="admin-crawled-mini-card" style={{ animationDelay: `${delay}ms` }}>
        <Box style={{
          width: 32, height: 32, borderRadius: 10, background: iconBg,
          display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 6,
        }}>
          <Icon size={16} color="white" />
        </Box>
        <Text fw={800} style={{ fontSize: 22, lineHeight: 1, color: '#1e293b' }}>{animatedValue}</Text>
        <Text size="xs" fw={600} style={{ color }}>{label}</Text>
      </Box>
    </UnstyledButton>
  );
}

/* ---------- Skeleton ---------- */
function DashboardSkeleton() {
  return (
    <Box py="md" px="md">
      <Stack gap={12}>
        <Group grow gap={12}>
          <Box className="admin-skeleton" style={{ height: 130 }} />
          <Box className="admin-skeleton" style={{ height: 130 }} />
        </Group>
        <Group grow gap={10}>
          {[1, 2, 3].map((i) => (
            <Box key={i} className="admin-skeleton" style={{ height: 170, borderRadius: 18 }} />
          ))}
        </Group>
        <Group grow gap={10}>
          {[1, 2, 3].map((i) => (
            <Box key={i} className="admin-skeleton" style={{ height: 170, borderRadius: 18 }} />
          ))}
        </Group>
      </Stack>
    </Box>
  );
}

/* ---------- Main Page ---------- */
function Page() {
  const navigate = useNavigate();
  const { t } = useTranslation('admin');
  const [stats, isLoading] = useUnit([$dashboardStats, $isLoadingDashboard]);
  const [crawledStats] = useUnit([$crawledStats]);
  const initializedRef = useRef(false);

  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;
    fetchDashboardStats();
    fetchCrawledStatsFx();
  }, []);

  if (isLoading || !stats) {
    return <DashboardSkeleton />;
  }

  return (
    <Box className="admin-page-enter" py="md" px="md">
      {/* Pending Actions */}
      <Box className="admin-section-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <IconArrowUpRight size={14} color="#f59e0b" />
        {t('dashboard.requiresAttention')}
      </Box>
      <Group grow gap={12} mb="xl">
        <PendingCard
          title={t('dashboard.pendingUsers')}
          value={stats.pending_users}
          icon={IconClock}
          gradient="admin-gradient-pending"
          delay={0}
          onClick={() => navigate('/admin/users?status=pending')}
        />
        <PendingCard
          title={t('dashboard.pendingListings')}
          value={stats.pending_listings}
          icon={IconClock}
          gradient="admin-gradient-pending"
          delay={80}
          onClick={() => navigate('/admin/listings?status=pending')}
        />
      </Group>

      {/* Crawled Data Stats */}
      <Box className="admin-section-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <IconWorldSearch size={14} color="#8b5cf6" />
        {t('dashboard.crawledData')}
      </Box>
      <Group grow gap={10} mb="xl">
        <CrawledMiniCard
          label="OLX.uz"
          count={crawledStats?.olx_count || 0}
          icon={IconWorldSearch}
          color="#059669"
          iconBg="linear-gradient(135deg, #10b981, #059669)"
          delay={120}
          onClick={() => navigate('/admin/crawled')}
        />
        <CrawledMiniCard
          label="Telegram"
          count={crawledStats?.telegram_count || 0}
          icon={IconBrandTelegram}
          color="#0284c7"
          iconBg="linear-gradient(135deg, #0ea5e9, #0284c7)"
          delay={160}
          onClick={() => navigate('/admin/crawled')}
        />
      </Group>

      {/* User Stats with Rings */}
      <Box className="admin-section-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <IconUsers size={14} color="#6366f1" />
        {t('dashboard.userStats')}
      </Box>
      <Group grow gap={10} mb="xl">
        <ProgressRing
          value={stats.total_users}
          total={stats.total_users}
          label={t('dashboard.total')}
          ofTotalText={t('dashboard.of', { total: stats.total_users })}
          color="#6366f1"
          glowColor="rgba(99, 102, 241, 0.3)"
          delay={200}
          onClick={() => navigate('/admin/users')}
        />
        <ProgressRing
          value={stats.approved_users}
          total={stats.total_users}
          label={t('dashboard.approved')}
          ofTotalText={t('dashboard.of', { total: stats.total_users })}
          color="#10b981"
          glowColor="rgba(16, 185, 129, 0.3)"
          delay={280}
          onClick={() => navigate('/admin/users?status=approved')}
        />
        <ProgressRing
          value={stats.rejected_users}
          total={stats.total_users}
          label={t('dashboard.rejected')}
          ofTotalText={t('dashboard.of', { total: stats.total_users })}
          color="#f43f5e"
          glowColor="rgba(244, 63, 94, 0.3)"
          delay={360}
          onClick={() => navigate('/admin/users?status=rejected')}
        />
      </Group>

      {/* Listing Stats with Rings */}
      <Box className="admin-section-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <IconBuildingSkyscraper size={14} color="#06b6d4" />
        {t('dashboard.listingStats')}
      </Box>
      <Group grow gap={10}>
        <ProgressRing
          value={stats.total_listings}
          total={stats.total_listings}
          label={t('dashboard.total')}
          ofTotalText={t('dashboard.of', { total: stats.total_listings })}
          color="#06b6d4"
          glowColor="rgba(6, 182, 212, 0.3)"
          delay={440}
          onClick={() => navigate('/admin/listings')}
        />
        <ProgressRing
          value={stats.approved_listings}
          total={stats.total_listings}
          label={t('dashboard.approved')}
          ofTotalText={t('dashboard.of', { total: stats.total_listings })}
          color="#10b981"
          glowColor="rgba(16, 185, 129, 0.3)"
          delay={520}
          onClick={() => navigate('/admin/listings?status=approved')}
        />
        <ProgressRing
          value={stats.rejected_listings}
          total={stats.total_listings}
          label={t('dashboard.rejected')}
          ofTotalText={t('dashboard.of', { total: stats.total_listings })}
          color="#f43f5e"
          glowColor="rgba(244, 63, 94, 0.3)"
          delay={600}
          onClick={() => navigate('/admin/listings?status=rejected')}
        />
      </Group>
    </Box>
  );
}

export const AdminDashboard = {
  route: '/admin',
  Page,
};
