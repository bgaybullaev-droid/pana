import { FC, lazy, Suspense } from 'react';
import { Box, Loader, Center } from '@mantine/core';
import type { BuyerListing } from '@shared/api/types';

// Lazy load sliders to reduce initial bundle size
const IOSSlider = lazy(() =>
  import('./IOSSlider').then((m) => ({ default: m.IOSSlider }))
);
const AndroidSlider = lazy(() =>
  import('./AndroidSlider').then((m) => ({ default: m.AndroidSlider }))
);

interface TikTokSliderProps {
  listings: BuyerListing[];
  onLoadMore: () => void;
  hasMore: boolean;
  onLike: (id: string) => void;
  onMessage: (id: string) => void;
  onShare: (id: string) => void;
}

// Platform detection
const isiOS = (): boolean => {
  return /iPhone/.test(navigator.userAgent);
};

const SliderFallback: FC = () => (
  <Box h="100vh" bg="black">
    <Center h="100%">
      <Loader color="white" />
    </Center>
  </Box>
);

export const TikTokSlider: FC<TikTokSliderProps> = (props) => {
  const isIOSDevice = isiOS();

  return (
    <Suspense fallback={<SliderFallback />}>
      {isIOSDevice ? <IOSSlider {...props} /> : <AndroidSlider {...props} />}
    </Suspense>
  );
};

export { IOSSlider } from './IOSSlider';
export { AndroidSlider } from './AndroidSlider';
