import { useState } from 'react';
import { Box, Image } from '@mantine/core';
import { IconPhoto } from '@tabler/icons-react';
import { radii } from '@app/styles/theme';

interface ListingImageThumbnailProps {
  src: string | null;
  size?: number;
}

export function ListingImageThumbnail({ src, size = 96 }: ListingImageThumbnailProps) {
  const [error, setError] = useState(false);

  return (
    <Box
      style={{
        width: size,
        height: size,
        borderRadius: radii.md,
        overflow: 'hidden',
        flexShrink: 0,
        backgroundColor: 'var(--mantine-color-gray-1)',
      }}
    >
      {src && !error ? (
        <Image src={src} alt="" w={size} h={size} fit="cover" onError={() => setError(true)} />
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
