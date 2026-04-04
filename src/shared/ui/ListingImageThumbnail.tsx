import { Box, Image } from '@mantine/core';
import { IconPhoto } from '@tabler/icons-react';

interface ListingImageThumbnailProps {
  src: string | null;
  size?: number;
}

export function ListingImageThumbnail({ src, size = 96 }: ListingImageThumbnailProps) {
  return (
    <Box
      style={{
        width: size,
        height: size,
        borderRadius: 10,
        overflow: 'hidden',
        flexShrink: 0,
        backgroundColor: 'var(--mantine-color-gray-1)',
      }}
    >
      {src ? (
        <Image src={src} alt="" w={size} h={size} fit="cover" />
      ) : (
        <Box
          style={{
            width: '100%',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <IconPhoto size={28} color="var(--mantine-color-gray-4)" />
        </Box>
      )}
    </Box>
  );
}
