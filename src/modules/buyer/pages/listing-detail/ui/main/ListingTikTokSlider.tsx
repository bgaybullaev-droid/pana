import { FC, useRef, useState, useEffect, useCallback } from 'react';
import { Box, Text, Transition } from '@mantine/core';
import { ListingSlideContent } from './ListingSlideContent';
import { ensureNearbyResolved } from '../../model';
import type { UnifiedListing } from '@shared/api/types';

interface ListingTikTokSliderProps {
  slideIds: string[];
  listingsMap: Record<string, UnifiedListing>;
  initialListingId: string;
  onLoadMore: () => void;
  hasMore: boolean;
  onLike: (id: string) => void;
  onShare: (id: string) => void;
}

// Full screen — no tab bar on listing detail
const SECTION_HEIGHT = '100vh';

// Only mount ListingSlideContent for slides within this distance from the
// current visible index.  Slides outside the window get a lightweight
// placeholder, which avoids creating Swiper instances and image requests
// for off-screen content.
const RENDER_WINDOW = 1;

export const ListingTikTokSlider: FC<ListingTikTokSliderProps> = ({
  slideIds,
  listingsMap,
  initialListingId,
  onLoadMore,
  hasMore,
  onLike,
  onShare,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const fetchNextPageRef = useRef(false);
  const [showGetReady, setShowGetReady] = useState(false);

  // Keep listings in original order — scroll to the initial listing instead of reordering
  const initialIndex = slideIds.indexOf(initialListingId);

  // Track the currently visible slide index so we can window-mount slides.
  // Initialised from the listing the user clicked.
  const [currentIndex, setCurrentIndex] = useState(
    () => (initialIndex >= 0 ? initialIndex : 0),
  );
  const currentIndexRef = useRef(currentIndex);

  // Scroll to the initial listing whenever its position changes (e.g. when
  // batched listings arrive and the target shifts from index 0 to index 89).
  // Also sync currentIndex — programmatic scrollTop doesn't fire scroll events.
  const prevInitialIndexRef = useRef(-1);
  useEffect(() => {
    const container = containerRef.current;
    if (!container || initialIndex < 0) return;

    // Skip if we already scrolled to this exact index
    if (prevInitialIndexRef.current === initialIndex) return;
    prevInitialIndexRef.current = initialIndex;

    const sectionHeight = container.clientHeight;
    if (sectionHeight === 0) return;

    container.scrollTop = initialIndex * sectionHeight;
    currentIndexRef.current = initialIndex;
    setCurrentIndex(initialIndex);
  }, [initialIndex, slideIds.length]);

  // Reset fetch ref when slide count changes
  useEffect(() => {
    fetchNextPageRef.current = false;
  }, [slideIds.length]);

  // Auto-hide "Getting ready" text
  useEffect(() => {
    if (!showGetReady) return;
    const timer = setTimeout(() => setShowGetReady(false), 2000);
    return () => clearTimeout(timer);
  }, [showGetReady]);

  // Scroll handler — tracks visible index + infinite loading
  const handleScroll = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    const sectionHeight = container.clientHeight;
    if (sectionHeight === 0) return;

    const newIndex = Math.round(container.scrollTop / sectionHeight);

    // Update current index only when it actually changes to avoid re-renders
    if (newIndex !== currentIndexRef.current) {
      currentIndexRef.current = newIndex;
      setCurrentIndex(newIndex);
      // Trigger on-demand fetch for slides near the new position.
      // Pass the listing ID (not index) so the model can map to the
      // correct position in the full seedIds array.
      const visibleId = slideIds[newIndex];
      if (visibleId) {
        ensureNearbyResolved(visibleId);
      }
    }

    // Trigger load more when 2 sections from end
    if (
      newIndex >= slideIds.length - 2 &&
      hasMore &&
      !fetchNextPageRef.current
    ) {
      fetchNextPageRef.current = true;
      setShowGetReady(true);
      onLoadMore();
    }
  }, [slideIds, hasMore, onLoadMore]);

  if (slideIds.length === 0) {
    return (
      <Box
        h={SECTION_HEIGHT}
        display="flex"
        style={{ alignItems: 'center', justifyContent: 'center' }}
      >
        <Text c="white">No listings available</Text>
      </Box>
    );
  }

  return (
    <Box
      maw={500}
      mx="auto"
      w="100%"
      h={SECTION_HEIGHT}
      pos="relative"
    >
      {/* Getting Ready Text */}
      <Box pos="absolute" bottom={170} right={70} style={{ zIndex: 99 }}>
        <Transition mounted={showGetReady} transition="fade" duration={100}>
          {(styles) => (
            <Text
              size="md"
              fw={600}
              c="white"
              lh="15px"
              maw={200}
              ml={8}
              style={styles}
            >
              {/* Getting ready */}
            </Text>
          )}
        </Transition>
      </Box>

      {/* Scroll-snap container */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="tiktok-scroll-container"
        style={{
          height: '100%',
          overflowY: 'auto',
          scrollSnapType: 'y mandatory',
          WebkitOverflowScrolling: 'touch',
          msOverflowStyle: 'none',
          scrollbarWidth: 'none',
          touchAction: 'pan-y',
        }}
      >
        {slideIds.map((id, index) => {
          const isNearby = Math.abs(index - currentIndex) <= RENDER_WINDOW;
          const isActive = index === currentIndex;
          const listing = listingsMap[id];

          return (
            <div
              key={id}
              style={{
                height: SECTION_HEIGHT,
                scrollSnapAlign: 'start',
                scrollSnapStop: 'always',
                position: 'relative',
                background: '#000',
                overflow: 'hidden',
              }}
            >
              {isNearby && listing ? (
                <ListingSlideContent
                  listing={listing}
                  isActive={isActive}
                  onLike={onLike}
                  onShare={onShare}
                />
              ) : (
                // Lightweight placeholder — preserves scroll height, no Swiper / images
                <div style={{ width: '100%', height: '100%', background: '#000' }} />
              )}
            </div>
          );
        })}
      </div>
    </Box>
  );
};
