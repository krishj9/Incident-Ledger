/**
 * StatusBadge — incident workflow status chip
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { statusMeta, colors, radius, typography } from '../tokens';

export function StatusBadge({ status }: { status: string }) {
  const meta = statusMeta[status] ?? { color: colors.slate, label: status };

  return (
    <View style={[styles.badge, { borderColor: meta.color + '40', backgroundColor: meta.color + '12' }]}>
      <Text style={[styles.text, { color: meta.color }]}>{meta.label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: radius.pill,
    borderWidth: 1,
    alignSelf: 'flex-start',
  },
  text: {
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.semibold as any,
  },
});
