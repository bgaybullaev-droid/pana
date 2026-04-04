import { FC, useRef, useState, useEffect, useCallback } from 'react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Mousewheel, Virtual } from 'swiper/modules';
import type { Swiper as SwiperType } from 'swiper';
import { Box, Text, Transition } from '@mantine/core';
import { SlideContent } from './SlideContent';
import type { BuyerListing } from '@shared/api/types';

import 'swiper/css';
import 'swiper/css/mousewheel';
import './styles.css';

interface IOSSliderProps {
  listings: BuyerListing[];
  onLoadMore: () => void;
  hasMore: boolean;
  onLike: (id: string) => void;
  onMessage: (id: string) => void;
  onShare: (id: string) => void;
}

export const IOSSlider: FC<IOSSliderProps> = ({
  listings,
  onLoadMore,
  hasMore,
  onLike,
  onMessage,
  onShare,
}) => {
  const swiperRef = useRef<SwiperType | null>(null);
  const fetchNextPageRef = useRef(false);
  const [showGetReady, setShowGetReady] = useState(false);

  // Reset fetch ref when listings change
  useEffect(() => {
    fetchNextPageRef.current = false;
  }, [listings.length]);

  // Auto-hide "Getting ready" text
  useEffect(() => {
    if (!showGetReady) return;
    const timer = setTimeout(() => setShowGetReady(false), 2000);
    return () => clearTimeout(timer);
  }, [showGetReady]);

  const handleSlideChange = useCallback(
    (swiper: SwiperType) => {
      const currentIndex = swiper.activeIndex;

      // Infinite scroll trigger - load more when near the end
      if (
        currentIndex >= listings.length - 2 &&
        hasMore &&
        !fetchNextPageRef.current
      ) {
        fetchNextPageRef.current = true;
        setShowGetReady(true);
        onLoadMore();
      }
    },
    [listings.length, hasMore, onLoadMore]
  );

  if (listings.length === 0) {
    return (
      <Box
        h="100vh"
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
      h="100vh"
      pos="relative"
      style={{ transition: 'all 0.5s linear' }}
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

      <Swiper
        onSwiper={(swiper) => {
          swiperRef.current = swiper;
        }}
        direction="vertical"
        slidesPerView={1}
        speed={600}
        mousewheel={{
          sensitivity: 1,
          thresholdDelta: 30,
        }}
        touchRatio={1}
        threshold={10}
        resistance={true}
        resistanceRatio={0.85}
        modules={[Mousewheel, Virtual]}
        virtual
        onSlideChange={handleSlideChange}
        style={{ height: '100vh', width: '100%' }}
      >
        {listings.map((listing, index) => (
          <SwiperSlide key={listing.id} virtualIndex={index}>
            <div className={`section s${index}`} style={{ height: '100vh' }}>
              <SlideContent
                listing={listing}
                onLike={onLike}
                onMessage={onMessage}
                onShare={onShare}
              />
            </div>
          </SwiperSlide>
        ))}
      </Swiper>
    </Box>
  );
};
