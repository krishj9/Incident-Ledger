/**
 * SeverityBadge — color-coded severity label chip
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, severity as severityMeta, radius, typography } from '../tokens';

interface Props {
  level: string;
  size?: 'sm' | 'md';
}

export function SeverityBadge({ level, size = 'md' }: Props) {
  const meta = severityMeta[level as keyof typeof severityMeta] ?? {
    color: colors.slate,
    bg: colors.offWhite,
    border: colors.border,
    label: level.toUpperCase(),
  };

  const isCritical = level === 'critical';

  return (
    <View style={[
      styles.badge,
      { backgroundColor: meta.bg, borderColor: meta.border },
      size === 'sm' && styles.sm,
      isCritical && styles.criticalPulse,
    ]}>
      {isCritical && <View style={styles.dot} />}
      <Text style={[
        styles.text,
        { color: meta.color },
        size === 'sm' && styles.textSm,
      ]}>
        {meta.label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.pill,
    borderWidth: 1,
    gap: 5,
    alignSelf: 'flex-start',
  },
  sm: {
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  criticalPulse: {
    // Web-only: animation via CSS shadow
    shadowColor: colors.critical,
    shadowOpacity: 0.3,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 0 },
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.critical,
  },
  text: {
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.bold as any,
    letterSpacing: 0.6,
  },
  textSm: {
    fontSize: 10,
  },
});
