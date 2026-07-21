/**
 * RedlineViewer — shows diff between two text versions with word-level highlighting.
 * Highlights additions (green) and removals (red).
 * Shows edit_reason above the diff.
 */
import React, { useMemo } from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { colors, typography, spacing, radius } from '../tokens';

interface DiffPart {
  value: string;
  added?: boolean;
  removed?: boolean;
}

function simpleDiff(original: string, edited: string): DiffPart[] {
  // Word-level diff using Longest Common Subsequence approach
  const origWords = original.split(/(\s+)/);
  const editWords = edited.split(/(\s+)/);

  const m = origWords.length;
  const n = editWords.length;

  // Build LCS table
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (origWords[i - 1] === editWords[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  // Backtrack to find diff
  const parts: DiffPart[] = [];
  let i = m, j = n;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && origWords[i - 1] === editWords[j - 1]) {
      parts.unshift({ value: origWords[i - 1] });
      i--; j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      parts.unshift({ value: editWords[j - 1], added: true });
      j--;
    } else {
      parts.unshift({ value: origWords[i - 1], removed: true });
      i--;
    }
  }

  // Merge consecutive same-type parts
  const merged: DiffPart[] = [];
  for (const part of parts) {
    const last = merged[merged.length - 1];
    if (last && !!last.added === !!part.added && !!last.removed === !!part.removed) {
      last.value += part.value;
    } else {
      merged.push({ ...part });
    }
  }
  return merged;
}

interface Props {
  original: string;
  edited: string;
  editReason: string;
}

export function RedlineViewer({ original, edited, editReason }: Props) {
  const diff = useMemo(() => simpleDiff(original, edited), [original, edited]);
  const hasChanges = diff.some(p => p.added || p.removed);

  return (
    <View style={styles.container}>
      <View style={styles.reasonRow}>
        <Text style={styles.reasonLabel}>Edit Reason</Text>
        <Text style={styles.reasonText}>{editReason}</Text>
      </View>

      {!hasChanges && (
        <View style={styles.noChange}>
          <Text style={styles.noChangeText}>No textual differences found between versions.</Text>
        </View>
      )}

      {hasChanges && (
        <ScrollView style={styles.diffBox} showsVerticalScrollIndicator={false}>
          <Text style={styles.diffText}>
            {diff.map((part, idx) => (
              <Text
                key={idx}
                style={[
                  styles.diffPart,
                  part.added && styles.added,
                  part.removed && styles.removed,
                ]}
              >
                {part.value}
              </Text>
            ))}
          </Text>
        </ScrollView>
      )}

      <View style={styles.legend}>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: colors.added }]} />
          <Text style={styles.legendLabel}>Added</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: colors.removed }]} />
          <Text style={styles.legendLabel}>Removed</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.md,
  },
  reasonRow: {
    backgroundColor: colors.accentLight,
    borderLeftWidth: 3,
    borderLeftColor: colors.accent,
    borderRadius: radius.sm,
    padding: spacing.md,
    gap: 4,
  },
  reasonLabel: {
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.bold as any,
    color: colors.accent,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
  },
  reasonText: {
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.sm,
    color: colors.navyLight,
    lineHeight: 20,
  },
  noChange: {
    backgroundColor: colors.offWhite,
    borderRadius: radius.md,
    padding: spacing.lg,
    alignItems: 'center',
  },
  noChangeText: {
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.sm,
    color: colors.slate,
    fontStyle: 'italic',
  },
  diffBox: {
    backgroundColor: colors.offWhite,
    borderRadius: radius.md,
    padding: spacing.lg,
    maxHeight: 300,
  },
  diffText: {
    fontFamily: "'Georgia', serif",
    fontSize: typography.sizes.md,
    lineHeight: 26,
    color: colors.navyLight,
  },
  diffPart: {
    fontFamily: "'Georgia', serif",
  },
  added: {
    backgroundColor: colors.addedBg,
    color: colors.added,
    textDecorationLine: 'underline',
  },
  removed: {
    backgroundColor: colors.removedBg,
    color: colors.removed,
    textDecorationLine: 'line-through',
  },
  legend: {
    flexDirection: 'row',
    gap: spacing.lg,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  legendLabel: {
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.xs,
    color: colors.slate,
  },
});
