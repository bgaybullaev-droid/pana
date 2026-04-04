import { useEffect, useCallback, useRef } from 'react';
import { useUnit } from 'effector-react';
import { Box, LoadingOverlay, ActionIcon } from '@mantine/core';
import { IconArrowLeft } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { useTelegram } from '@app/providers/useTelegram';
import { getListingShareUrl } from '@shared/lib/constants';
import { TikTokSlider } from '@modules/buyer/pages/listing-detail/ui/main/Sliders';
import {
  $listings,
  $isLoading,
  $hasMore,
  pageOpened,
  loadMore,
  likeToggled,
  shareClicked,
  messageClicked,
} from '../../model';

function Page() {
  const navigate = useNavigate();
  const { webApp } = useTelegram();
  const [listings, isLoading, hasMore] = useUnit([$listings, $isLoading, $hasMore]);
  const initializedRef = useRef(false);

  useEffect(() => {
    // Prevent double call in React StrictMode
    if (initializedRef.current) return;
    initializedRef.current = true;
    pageOpened();
  }, []);

  const handleLike = useCallback(
    (id: string) => {
      webApp?.HapticFeedback.impactOccurred('light');
      likeToggled(id);
    },
    [webApp]
  );

  const handleMessage = useCallback(
    (id: string) => {
      webApp?.HapticFeedback.impactOccurred('light');
      messageClicked(id);
      // Find listing and open Telegram link
      const listing = listings.find((l) => l.id === id);
      if (listing?.sellerUserName) {
        webApp?.openTelegramLink(`https://t.me/${listing.sellerUserName}`);
      }
    },
    [webApp, listings]
  );

  const handleShare = useCallback(
    (id: string) => {
      webApp?.HapticFeedback.impactOccurred('light');
      shareClicked(id);
      webApp?.openTelegramLink(getListingShareUrl(id));
    },
    [webApp]
  );

  const handleBack = () => {
    navigate(-1);
  };

  if (isLoading && listings.length === 0) {
    return <LoadingOverlay visible />;
  }

  return (
    <Box h="100vh" w="100%" pos="relative" style={{ overflow: 'hidden' }}>
      {/* Back Button */}
      <ActionIcon
        variant="transparent"
        size={56}
        onClick={handleBack}
        style={{
          position: "fixed",
          top: 12,
          left: 12,
          zIndex: 99,
          backgroundColor: "rgba(255, 255, 255, 0.65)",
          backdropFilter: "blur(20px) saturate(180%)",
          WebkitBackdropFilter: "blur(20px) saturate(180%)",
          border: "1px solid rgba(255, 255, 255, 0.5)",
          boxShadow: "0 4px 20px rgba(0, 0, 0, 0.04)",
          borderRadius: "50%",
        }}
      >
        <IconArrowLeft size={24} color="#868e96" />
      </ActionIcon>

      {/* TikTok Slider */}
      <TikTokSlider
        listings={listings}
        onLoadMore={loadMore}
        hasMore={hasMore}
        onLike={handleLike}
        onMessage={handleMessage}
        onShare={handleShare}
      />
    </Box>
  );
}

export const Browse = {
  route: '/browse',
  Page,
};
