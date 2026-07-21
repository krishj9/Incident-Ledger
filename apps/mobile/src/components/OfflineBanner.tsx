import React from 'react';
import { useNetworkState } from '../hooks/useNetworkState';
import { WifiOff } from 'lucide-react-native';
import { XStack, Text } from 'tamagui';

export function OfflineBanner() {
  const { isOffline } = useNetworkState();

  if (!isOffline) {
    return null;
  }

  return (
    <XStack
      backgroundColor="$red10"
      alignItems="center"
      justifyContent="center"
      paddingVertical="$2"
      paddingHorizontal="$4"
      gap="$2"
    >
      <WifiOff size={16} color="#fff" />
      <Text color="#fff" fontSize="$3" fontWeight="600">
        You are offline
      </Text>
    </XStack>
  );
}
