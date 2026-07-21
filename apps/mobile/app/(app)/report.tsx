import React from 'react';
import { YStack, Text } from 'tamagui';

export default function NewReportTab() {
  return (
    <YStack flex={1} justifyContent="center" alignItems="center" backgroundColor="$background">
      <Text fontSize="$6" fontWeight="600" color="$color">
        New Report Wizard
      </Text>
      <Text marginTop="$2" color="$colorFocus">
        (Placeholder for Prompt 1.6)
      </Text>
    </YStack>
  );
}
