import { FC, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUnit } from 'effector-react';
import { Box, Container, Loader, Center, Text, Stack, Skeleton } from '@mantine/core';
import Masonry from 'react-masonry-css';
import { MasonryListingCard } from '@shared/ui/MasonryListingCard';
import { $listings, $isLoading, $hasMore, loadMore } from '../../model';

import './ListingsGrid.css';

const breakpointColumns = {
  default: 2, // Always 2 columns for mobile-first
};

const skeletonHeights = [250, 280, 320, 240];

export const ListingsGrid: FC = () => {
  const navigate = useNavigate();
  const [listings, isLoading, hasMore] = useUnit([$listings, $isLoading, $hasMore]);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const loadMoreRef = useRef<HTMLDivElement | null>(null);

  const handleCardClick = useCallback(
    (id: string) => {
      navigate(`/listings/${id}`);
    },
    [navigate]
  );

  // Infinite scroll with IntersectionObserver
  useEffect(() => {
    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !isLoading) {
          loadMore();
        }
      },
      { threshold: 0.1 }
    );

    if (loadMoreRef.current) {
      observerRef.current.observe(loadMoreRef.current);
    }

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [hasMore, isLoading]);

  // Show skeletons while initial loading
  if (isLoading && listings.length === 0) {
    return (
      <Box bg="gray.1" mih="100vh">
        <Container className="listings-container">
          <Masonry
            breakpointCols={breakpointColumns}
            className="listings-masonry-grid"
            columnClassName="listings-masonry-column"
          >
            {[...Array(4)].map((_, index) => (
              <Skeleton key={index} height={skeletonHeights[index % 4]} radius="md" mb={8} />
            ))}
          </Masonry>
        </Container>
      </Box>
    );
  }

  // Empty state
  if (!isLoading && listings.length === 0) {
    return (
      <Box bg="gray.1" mih="100vh">
        <Container className="listings-container">
          <Center py="xl">
            <Text c="dimmed">No listings found</Text>
          </Center>
        </Container>
      </Box>
    );
  }

  return (
    <Box bg="gray.1" mih="100vh">
      <Container className="listings-container">
        <Masonry
          breakpointCols={breakpointColumns}
          className="listings-masonry-grid"
          columnClassName="listings-masonry-column"
        >
          {listings.map((item) => (
            <MasonryListingCard key={item.id} listing={item} onClick={handleCardClick} />
          ))}
        </Masonry>

        {/* Load more trigger */}
        <div ref={loadMoreRef} style={{ height: 1 }} />

        {/* Loading indicator */}
        {isLoading && (
          <Center py="xl">
            <Stack align="center" gap="xs">
              <Loader size="sm" color="blue.5" />
              <Text size="xs" fw={700} c="blue.5">
                Loading...
              </Text>
            </Stack>
          </Center>
        )}
      </Container>
    </Box>
  );
};
