import React, { useEffect, useState, useMemo } from 'react';
import {
  Container,
  Stack,
  Text,
  Group,
  Menu,
  ActionIcon,
  Box,
  Skeleton,
  TextInput,
  ScrollArea,
  Portal,
  UnstyledButton
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconSearch,
  IconX,
  IconBuilding,
  IconCheck,
  IconTrash,
  IconDotsVertical,
  IconEye,
  IconPhone,
  IconInfoCircle,
  IconArrowLeft,
  IconX as IconXIcon, // Alias to avoid conflict with IconX used in TextInput
} from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import { InnerPage } from '@shared/ui/InnerPage';
import { EmptyState } from '@shared/ui/EmptyState';
import { ListingRow } from '@shared/ui/ListingRow';
import { ListingTikTokSlider } from '@modules/buyer/pages/listing-detail/ui/main/ListingTikTokSlider';
import { radii, shadows } from '@app/styles/theme';
import { translateDistrict } from '@shared/lib/regions';
import { fetchSellerOLXListings, fetchSellerTelegramListings } from '@modules/seller/shared/api/sellerCrawledListings';
import type { OLXListing, TelegramListing } from '@shared/api/types';

type Platform = 'all' | 'olx' | 'telegram';

interface UnifiedCard {
  id: string;
  source: Platform;
  price: number;
  currency: string;
  title: string;
  imageUrl: string | null;
  images: { url: string }[];
  rooms: number | null;
  area: number | null;
  district: string | null;
  views_count?: number;
  contacts_count?: number;
}

function Page() {
  const { t } = useTranslation('seller');
  const { t: tBuyer } = useTranslation('buyer');

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPlatform, setSelectedPlatform] = useState<Platform>('all');
  const [showInfo, setShowInfo] = useState(true); // () => localStorage.getItem('hide_found_info') !== 'true'
  const [activeListingId, setActiveListingId] = useState<string | null>(null);


  const [isLoading, setIsLoading] = useState(true);
  const [olxListings, setOlxListings] = useState<OLXListing[]>([]);
  const [telegramListings, setTelegramListings] = useState<TelegramListing[]>([]);

  useEffect(() => {
    let active = true;
    const loadListings = async () => {
      setIsLoading(true);
      try {
        if (selectedPlatform === 'all') {
          const [resOlx, resTg] = await Promise.all([
            fetchSellerOLXListings({ page: 1, per_page: 50 }).catch(() => ({ items: [] })),
            fetchSellerTelegramListings({ page: 1, per_page: 50 }).catch(() => ({ items: [] })),
          ]);
          if (active) {
            setOlxListings(resOlx.items);
            setTelegramListings(resTg.items);
          }
        } else if (selectedPlatform === 'olx') {
          const res = await fetchSellerOLXListings({ page: 1, per_page: 50 });
          if (active) setOlxListings(res.items);
        } else if (selectedPlatform === 'telegram') {
          const res = await fetchSellerTelegramListings({ page: 1, per_page: 50 });
          if (active) setTelegramListings(res.items);
        }
      } catch (err) {
        console.error('Failed to load crawled listings', err);
      } finally {
        if (active) setIsLoading(false);
      }
    };
    loadListings();
    return () => { active = false; };
  }, [selectedPlatform]);

  const propertyTypeLabel = (type: string) => {
    const map: Record<string, string> = {
      apartment: t('propertyTypes.apartment', 'Apartments'),
      house: t('propertyTypes.house', 'Houses'),
      commercial: t('propertyTypes.commercial', 'Commercial'),
      land: t('propertyTypes.land', 'Land'),
    };
    return map[type] || type;
  };

  const unifiedCards = useMemo((): UnifiedCard[] => {
    const cards: UnifiedCard[] = [];

    if (selectedPlatform === 'olx' || selectedPlatform === 'all') {
      for (const l of olxListings) {
        const title = `${l.rooms ? `${l.rooms}-${t('listings.rooms')} ` : ''}${propertyTypeLabel(l.property_type)}${l.district ? ` ${t('listings.inDistrict', { district: translateDistrict(l.district, t) })}` : ''}`;
        
        cards.push({
          id: l.id,
          source: 'olx',
          price: l.price,
          currency: l.currency,
          title,
          imageUrl: (l.images && l.images.length > 0) ? (typeof l.images[0] === 'string' ? l.images[0] : (l.images[0] as any).url) : null,
          images: l.images ? l.images.map((img: any) => ({ url: typeof img === 'string' ? img : img.url })) : [],
          rooms: l.rooms,
          area: l.area_sqm,
          district: l.district,
          views_count: l.views_count ?? 0,
        });
      }
    }
    
    if (selectedPlatform === 'telegram' || selectedPlatform === 'all') {
      for (const l of telegramListings) {
        const title = `${l.rooms ? `${l.rooms}-${t('listings.rooms')} ` : ''}${propertyTypeLabel(l.property_type)}${l.district ? ` ${t('listings.inDistrict', { district: translateDistrict(l.district, t) })}` : ''}`;

        cards.push({
          id: l.id,
          source: 'telegram',
          price: l.price,
          currency: l.currency,
          title,
          imageUrl: (l.images && l.images.length > 0) ? (typeof l.images[0] === 'string' ? l.images[0] : (l.images[0] as any).url) : null,
          images: l.images ? l.images.map((img: any) => ({ url: typeof img === 'string' ? img : img.url })) : [],
          rooms: l.rooms,
          area: l.area_sqm,
          district: l.district,
        });
      }
    }

    if (searchQuery.trim() !== '') {
        const query = searchQuery.toLowerCase();
        return cards.filter(c => c.title.toLowerCase().includes(query) || (c.district && translateDistrict(c.district, t).toLowerCase().includes(query)));
    }

    return cards;
  }, [olxListings, telegramListings, selectedPlatform, searchQuery, t]);

  const handleClaim = (e: React.MouseEvent | null, _id: string) => {
    if (e) e.stopPropagation();
    notifications.show({ title: 'Информация', message: 'Действие "Это моё" пока в разработке', color: 'blue' });
  };

  const handleReject = (e: React.MouseEvent | null, _id: string) => {
    if (e) e.stopPropagation();
    notifications.show({ title: 'Информация', message: 'Действие "Не моё" пока в разработке', color: 'orange' });
  };

  const ALL_PLATFORMS: { value: Platform; label: string }[] = [
    { value: 'all', label: t('common.all', 'Все') },
    { value: 'olx', label: 'OLX' },
    { value: 'telegram', label: 'Telegram' },
  ];

  // Mockup data to show if arrays are empty
  const getMockups = (): UnifiedCard[] => {
    const realEstateImages = [
      "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1613490493576-7fde63acd811?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1600607687940-47a04fdd38ca?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1600566753376-12c8ab7fb75b?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1600585154542-a8436a0dc22e?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1600121848594-d8644e57abab?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1513584684374-8bdb7489feef?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1583608205776-bfd35f0d9f83?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1568605114967-8130f3a36994?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1600573472591-ee6b68d14c68?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1600607687644-c7171b42498f?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1200&q=80"
    ];

    const generateImages = (index: number) => {
      // Rotate through the curated list so they are varied
      const start = (index * 3) % realEstateImages.length;
      return [
        { url: realEstateImages[start] },
        { url: realEstateImages[(start + 1) % realEstateImages.length] },
        { url: realEstateImages[(start + 2) % realEstateImages.length] },
      ];
    };

    const olxMockups: UnifiedCard[] = [
        { id: 'mock-olx-1', source: 'olx', price: 45000, currency: 'USD', title: '2-комн. Квартира Юнусабадский район', imageUrl: realEstateImages[0], images: generateImages(0), rooms: 2, area: 55, district: 'yunusabadskiy', views_count: 120 },
        { id: 'mock-olx-2', source: 'olx', price: 120000, currency: 'USD', title: 'Современный дом в Мирзо-Улугбекском районе', imageUrl: realEstateImages[1], images: generateImages(1), rooms: 5, area: 250, district: 'mirzo-ulugbekskiy', views_count: 45 },
        { id: 'mock-olx-3', source: 'olx', price: 32000, currency: 'USD', title: '1-комн. Квартира Чиланзар', imageUrl: realEstateImages[2], images: generateImages(2), rooms: 1, area: 36, district: 'chilanzarskiy', views_count: 310 },
        { id: 'mock-olx-4', source: 'olx', price: 85000, currency: 'USD', title: '3-комн. Квартира Яккасарайский район', imageUrl: realEstateImages[3], images: generateImages(3), rooms: 3, area: 90, district: 'yakkasarayskiy', views_count: 85 },
        { id: 'mock-olx-5', source: 'olx', price: 150000, currency: 'USD', title: 'Евродом в Сергелийском районе', imageUrl: realEstateImages[4], images: generateImages(4), rooms: 6, area: 300, district: 'sergeliyskiy', views_count: 12 },
        { id: 'mock-olx-6', source: 'olx', price: 62000, currency: 'USD', title: '2-комн. Квартира Мирабадский район', imageUrl: realEstateImages[5], images: generateImages(5), rooms: 2, area: 68, district: 'mirabadskiy', views_count: 220 },
        { id: 'mock-olx-7', source: 'olx', price: 110000, currency: 'USD', title: '4-комн. Квартира Шайхантахурский район', imageUrl: realEstateImages[6], images: generateImages(6), rooms: 4, area: 120, district: 'shayhantahurskiy', views_count: 67 },
        { id: 'mock-olx-8', source: 'olx', price: 48000, currency: 'USD', title: 'Участок 4 сотки Алмазарский район', imageUrl: realEstateImages[7], images: generateImages(7), rooms: null, area: 400, district: 'almazarskiy', views_count: 19 },
        { id: 'mock-olx-9', source: 'olx', price: 55000, currency: 'USD', title: 'Новостройка 2-комн. Яшнобод', imageUrl: realEstateImages[8], images: generateImages(8), rooms: 2, area: 54, district: 'yashnobodskiy', views_count: 154 },
        { id: 'mock-olx-10', source: 'olx', price: 210000, currency: 'USD', title: 'Особняк 8 комн. Мирзо-Улугбекский', imageUrl: realEstateImages[9], images: generateImages(9), rooms: 8, area: 450, district: 'mirzo-ulugbekskiy', views_count: 23 },
    ];
    
    const tgMockups: UnifiedCard[] = [
        { id: 'mock-tg-1', source: 'telegram', price: 32000, currency: 'USD', title: '3-комн. Квартира Чиланзар', imageUrl: realEstateImages[2], images: generateImages(2), rooms: 3, area: 72, district: 'chilanzarskiy' },
        { id: 'mock-tg-2', source: 'telegram', price: 800, currency: 'USD', title: 'Аренда 2-комн. Мирабадский', imageUrl: realEstateImages[5], images: generateImages(5), rooms: 2, area: 65, district: 'mirabadskiy' },
        { id: 'mock-tg-3', source: 'telegram', price: 42000, currency: 'USD', title: 'Срочно 2-комн. Сергели', imageUrl: realEstateImages[8], images: generateImages(8), rooms: 2, area: 50, district: 'sergeliyskiy' },
        { id: 'mock-tg-4', source: 'telegram', price: 105000, currency: 'USD', title: 'Дом 4 сотки Учтепа', imageUrl: realEstateImages[1], images: generateImages(11), rooms: 5, area: 180, district: 'uchtepinskiy' },
        { id: 'mock-tg-5', source: 'telegram', price: 65000, currency: 'USD', title: '3-комн. новостройка Яккасарай', imageUrl: realEstateImages[4], images: generateImages(14), rooms: 3, area: 78, district: 'yakkasarayskiy' },
        { id: 'mock-tg-6', source: 'telegram', price: 54000, currency: 'USD', title: 'Юнусабад 3 квартал 2-комн.', imageUrl: realEstateImages[0], images: generateImages(6), rooms: 2, area: 55, district: 'yunusabadskiy' },
        { id: 'mock-tg-7', source: 'telegram', price: 1500, currency: 'USD', title: 'Аренда дома на Ц-1', imageUrl: realEstateImages[3], images: generateImages(7), rooms: 4, area: 150, district: 'tashkent_central' },
        { id: 'mock-tg-8', source: 'telegram', price: 28000, currency: 'USD', title: 'Участок Зангиота', imageUrl: realEstateImages[7], images: generateImages(17), rooms: null, area: 600, district: 'tashkent_region' },
        { id: 'mock-tg-9', source: 'telegram', price: 39000, currency: 'USD', title: 'Квартира студия Мирзо-Улугбек', imageUrl: realEstateImages[9], images: generateImages(19), rooms: 1, area: 40, district: 'mirzo-ulugbekskiy' },
        { id: 'mock-tg-10', source: 'telegram', price: 77000, currency: 'USD', title: '4-комн. Шайхантахур панельный', imageUrl: realEstateImages[6], images: generateImages(10), rooms: 4, area: 92, district: 'shayhantahurskiy' },
    ];
      
    if (selectedPlatform === 'all') {
      return [...olxMockups, ...tgMockups];
    } else if (selectedPlatform === 'olx') {
      return olxMockups;
    } else {
      return tgMockups;
    }
  };

  const displayedCards = unifiedCards.length > 0 ? unifiedCards : (isLoading ? [] : getMockups());

  const listingsMap = useMemo(() => {
    const map: Record<string, any> = {};
    displayedCards.forEach((c) => {
      map[c.id] = {
        id: c.id,
        source: c.source,
        price: c.price,
        currency: c.currency,
        title: c.title,
        description: c.title,
        property_type: 'apartment', // placeholder
        type: 'sell',
        images: c.images,
        favorites_count: 0,
        views_count: c.views_count || 0,
        rooms: c.rooms,
        area: c.area,
        district: c.district,
      };
    });
    return map;
  }, [displayedCards]);

  const slideIds = displayedCards.map((c) => c.id);

  return (
    <InnerPage title={t('dashboard.found', 'Найденные')} noPadding>
      <Container px="md" py="md">
        <Stack gap={16}>
          {/* Informational block */}
          {showInfo && (
            <Box style={{ animation: 'fade-in 0.4s ease-out' }}>
               <Box
                 style={{
                   background: '#f0f9ff',
                   border: '1px solid #bae6fd',
                   borderRadius: radii.md,
                   padding: 16,
                   boxShadow: shadows.sm,
                   position: 'relative',
                 }}
               >
                 <ActionIcon 
                    variant="subtle" 
                    color="gray" 
                    size="sm" 
                    style={{ position: 'absolute', top: 8, right: 8 }}
                    onClick={() => {
                      setShowInfo(false);
                      // localStorage.setItem('hide_found_info', 'true');
                    }}
                 >
                    <IconXIcon size={16} />
                 </ActionIcon>
                 <Group wrap="nowrap" align="flex-start" gap="sm" pr={24}>
                   <Box style={{ color: '#0284c7', marginTop: 2 }}>
                     <IconInfoCircle size={22} stroke={2} />
                   </Box>
                   <Box style={{ flex: 1 }}>
                     <Text size="sm" fw={700} c="dark.9">
                       {t('listings.crawledContextTitle', 'Ваши найденные объявления')}
                     </Text>
                     <Text size="13px" mt={4} fw={500} c="dimmed" lh={1.4}>
                       {t('listings.crawledContextDesc', 'Мы нашли эти объявления по вашему номеру на внешних площадках. Просмотрите их и нажмите «Это моё», чтобы управлять ими.')}
                     </Text>
                   </Box>
                 </Group>
               </Box>
            </Box>
          )}

          <Box style={{ animation: 'fade-in 0.4s ease-out 0.1s both' }}>
            <TextInput
              placeholder={tBuyer('search.title', 'Поиск')}
              radius="xl"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.currentTarget.value)}
              leftSection={<IconSearch size={20} color="#adb5bd" />}
              rightSection={
                searchQuery ? (
                  <ActionIcon variant="filled" size={18} radius="50%" color="gray.5" onClick={() => setSearchQuery('')}>
                    <IconX size={10} color="white" />
                  </ActionIcon>
                ) : null
              }
              styles={{
                input: {
                  backgroundColor: '#ffffff',
                  border: '1px solid #ced4da',
                  boxShadow: shadows.md,
                  height: 46,
                }
              }}
            />

            <ScrollArea scrollbarSize={0} type="never" offsetScrollbars={false} mt={12}>
              <Box style={{ display: "flex", gap: 8 }}>
                {ALL_PLATFORMS.map((platform) => {
                  const isSelected = selectedPlatform === platform.value;
                  return (
                    <Box
                      key={platform.value}
                      onClick={() => setSelectedPlatform(platform.value)}
                      style={{
                        padding: "5px 15px",
                        borderRadius: radii.full,
                        backgroundColor: isSelected ? "#228be6" : "#f1f3f5",
                        border: isSelected ? "1px solid #228be6" : "1px solid #ced4da",
                        boxShadow: shadows.md,
                        cursor: "pointer",
                        whiteSpace: "nowrap",
                        transition: "all 0.2s ease",
                      }}
                    >
                      <Text size="xs" fw={600} c={isSelected ? "white" : "gray.7"}>
                        {platform.label}
                      </Text>
                    </Box>
                  );
                })}
              </Box>
            </ScrollArea>
          </Box>

          {isLoading && displayedCards.length === 0 && (
            <Stack gap="sm" style={{ animation: 'fade-in-up 0.4s ease-out 0.1s both' }}>
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} height={100} radius={12} />
              ))}
            </Stack>
          )}

          {!isLoading && displayedCards.length === 0 && (
            <Box style={{ animation: 'fade-in-up 0.4s ease-out 0.1s both', marginTop: 32 }}>
              <EmptyState
                icon={searchQuery ? IconSearch : IconBuilding}
                title={searchQuery ? t('listings.emptySearch', 'Ничего не найдено') : t('listings.emptySource', 'Нет объявлений в этом источнике')}
                description=""
              />
            </Box>
          )}

          <Stack gap="xs">
            {displayedCards.map((card) => {
              const menuActions = (
                <Menu position="bottom-end">
                  <Menu.Target>
                    <ActionIcon variant="subtle" radius="xl" size="sm" style={{ backgroundColor: 'var(--mantine-color-gray-0)' }} onClick={(e) => { e.stopPropagation(); e.preventDefault(); }}>
                      <IconDotsVertical size={16} />
                    </ActionIcon>
                  </Menu.Target>
                  <Menu.Dropdown>
                    <Menu.Item leftSection={<IconCheck size={14} />} color="blue" onClick={(e) => handleClaim(e, card.id)}>
                      {t('listings.claimBtn', 'Это моё')}
                    </Menu.Item>
                    <Menu.Divider />
                    <Menu.Item leftSection={<IconTrash size={14} />} color="red" onClick={(e) => handleReject(e, card.id)}>
                      {t('listings.rejectBtn', 'Не моё')}
                    </Menu.Item>
                  </Menu.Dropdown>
                </Menu>
              );

              return (
                <Box key={card.id} onClick={() => setActiveListingId(card.id)} style={{ cursor: 'pointer' }}>
                  <ListingRow
                    imageUrl={card.imageUrl}
                    price={card.price}
                    currency={card.currency}
                    description={card.title}
                    district={card.district}
                    actions={
                      <Group gap={4} wrap="nowrap">
                        {menuActions}
                      </Group>
                    }
                  >
                    <Group gap={6} mt={4}>
                        <Group gap={4} wrap="nowrap">
                          {card.views_count !== undefined && card.views_count > 0 && (
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
                  </ListingRow>
                </Box>
              );
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
      </Container>
      {activeListingId && (
        <Portal>
          <Box
            style={{
              position: 'fixed',
              inset: 0,
              zIndex: 20000,
              backgroundColor: '#000',
            }}
          >
            <ListingTikTokSlider
              slideIds={slideIds}
              listingsMap={listingsMap}
              initialListingId={activeListingId}
              onLoadMore={() => {}}
              hasMore={false}
              mode="seller-crawled"
              onClaim={(id) => handleClaim(null, id)}
              onReject={(id) => handleReject(null, id)}
            />
            <Box
              style={{
                position: 'fixed',
                bottom: 0,
                left: 0,
                right: 0,
                paddingBottom: "env(safe-area-inset-bottom, 0px)",
                zIndex: 20001,
                pointerEvents: 'none',
              }}
            >
              <Box
                style={{
                  maxWidth: 500,
                  margin: '0 auto',
                  position: 'relative',
                  height: 72, // 4px top + 56px button + 12px bottom
                }}
              >
                <UnstyledButton
                  onClick={() => setActiveListingId(null)}
                  style={{
                    position: 'absolute',
                    bottom: 12,
                    right: 12,
                    width: 56,
                    height: 56,
                    borderRadius: "50%",
                    backgroundColor: "rgba(255, 255, 255, 0.65)",
                    backdropFilter: "blur(20px) saturate(180%)",
                    WebkitBackdropFilter: "blur(20px) saturate(180%)",
                    border: "1px solid rgba(255, 255, 255, 0.5)",
                    boxShadow: shadows.md,
                    pointerEvents: 'auto',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <IconArrowLeft size={24} stroke={1.8} color="#495057" />
                </UnstyledButton>
              </Box>
            </Box>
          </Box>
        </Portal>
      )}
    </InnerPage>
  );
}

export const Found = {
  route: '/seller/found',
  Page,
};
