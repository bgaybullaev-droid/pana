import { FC } from 'react';
import { Paper, Stack, UnstyledButton, Text, Group, ActionIcon, Loader, Center } from '@mantine/core';
import { IconClock, IconX } from '@tabler/icons-react';
import type { BuyerListing, SearchHistoryItem } from '@shared/api/types';

interface SearchResultsProps {
  historyItems: SearchHistoryItem[];
  searchResults: BuyerListing[];
  isSearching: boolean;
  onHistoryItemClick: (query: string) => void;
  onHistoryItemRemove: (id: string) => void;
  onClearHistory: () => void;
  onResultClick: (result: BuyerListing) => void;
}

export const SearchResults: FC<SearchResultsProps> = ({
  historyItems,
  searchResults,
  isSearching,
  onHistoryItemClick,
  onHistoryItemRemove,
  onClearHistory,
  onResultClick,
}) => {
  const hasHistory = historyItems.length > 0;
  const hasResults = searchResults.length > 0;

  if (!hasHistory && !hasResults && !isSearching) {
    return null;
  }

  return (
    <Paper
      shadow="sm"
      radius="0 0 10px 10px"
      p="md"
      mah={250}
      style={{
        transform: 'translateY(-10px)',
        overflow: 'auto',
        border: '1px solid #D7D7D7',
        boxShadow: '0px 1px 7px rgb(0 0 0 / 10%)',
      }}
    >
      {/* Loading indicator */}
      {isSearching && (
        <Center py="md">
          <Loader size="sm" />
        </Center>
      )}

      {/* Search Results */}
      {hasResults && !isSearching && (
        <Stack gap={0} mb="md">
          {searchResults.map((result) => (
            <UnstyledButton
              key={result.id}
              h={38}
              pl={13}
              style={{ borderBottom: '1px solid #f2f2f2' }}
              onClick={() => onResultClick(result)}
            >
              <Text size="sm">{result.name}</Text>
            </UnstyledButton>
          ))}
        </Stack>
      )}

      {/* History Header */}
      {hasHistory && (
        <>
          <Group justify="space-between" mb="sm">
            <Text size="md" fw={500} c="dark.6">
              History
            </Text>
            <UnstyledButton onClick={onClearHistory}>
              <Text size="xs" fw={500} c="dimmed">
                Clear all
              </Text>
            </UnstyledButton>
          </Group>

          {/* History Items */}
          <Stack gap={0}>
            {historyItems.map((item) => (
              <UnstyledButton
                key={item.id}
                h={38}
                pl={13}
                style={{ borderBottom: '1px solid #f2f2f2' }}
                onClick={() => onHistoryItemClick(item.query)}
              >
                <Group justify="space-between" w="100%">
                  <Group gap="xs">
                    <IconClock size={16} color="#9F9F9F" />
                    <Text size="sm">{item.query}</Text>
                  </Group>
                  <ActionIcon
                    variant="transparent"
                    onClick={(e) => {
                      e.stopPropagation();
                      onHistoryItemRemove(item.id);
                    }}
                  >
                    <IconX size={16} />
                  </ActionIcon>
                </Group>
              </UnstyledButton>
            ))}
          </Stack>
        </>
      )}
    </Paper>
  );
};
