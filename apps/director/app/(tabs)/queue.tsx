import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { useApi } from '../../src/hooks/useApi';
import { ReviewQueueItem } from '@incident-ledger/api-client';
import { SeverityBadge } from '../../src/components/SeverityBadge';
import { StatusBadge } from '../../src/components/StatusBadge';
import { colors, spacing, radius, typography, shadows } from '../../src/tokens';

export default function QueueScreen() {
  const router = useRouter();
  const api = useApi();
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQueue = async () => {
    try {
      const res = await api.getReviewQueue();
      
      // Sort logic: critical severity first, then by elapsed time (oldest first)
      const severityWeight: Record<string, number> = { critical: 3, high: 2, moderate: 1, low: 0 };
      const sorted = [...res.items].sort((a, b) => {
        const sA = severityWeight[a.severity] ?? 0;
        const sB = severityWeight[b.severity] ?? 0;
        if (sA !== sB) return sB - sA;
        return b.elapsed_seconds - a.elapsed_seconds;
      });
      
      setItems(sorted);
      setError(null);
    } catch (err) {
      console.error(err);
      setError('Failed to load review queue');
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch and auto-refresh every 30s
  useEffect(() => {
    fetchQueue();
    const interval = setInterval(fetchQueue, 30000);
    return () => clearInterval(interval);
  }, []);

  const formatElapsed = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    return `${hours}h ${mins % 60}m ago`;
  };

  const renderItem = ({ item }: { item: ReviewQueueItem }) => {
    const isUrgent = item.severity === 'critical' || item.severity === 'high';

    return (
      <TouchableOpacity 
        style={[styles.row, isUrgent && styles.rowUrgent]} 
        onPress={() => router.push(`/incidents/${item.incident_id}`)}
      >
        <View style={styles.colSeverity}>
          <SeverityBadge level={item.severity} />
        </View>
        <View style={styles.colStatus}>
          <StatusBadge status={item.status} />
        </View>
        <View style={styles.colCategory}>
          <Text style={styles.textMain}>{item.category.replace(/_/g, ' ')}</Text>
          <Text style={styles.textSub}>{item.location}</Text>
        </View>
        <View style={styles.colTime}>
          <Text style={styles.textMain}>{formatElapsed(item.elapsed_seconds)}</Text>
          {item.escalation_state && (
            <Text style={styles.textEscalated}>Escalated: {item.escalation_state}</Text>
          )}
        </View>
        <View style={styles.colAction}>
          <Text style={styles.actionText}>Review →</Text>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Review Queue</Text>
        <TouchableOpacity onPress={fetchQueue} style={styles.refreshBtn}>
          <Text style={styles.refreshText}>Refresh</Text>
        </TouchableOpacity>
      </View>

      {error && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}

      {loading && items.length === 0 ? (
        <View style={styles.centerBox}>
          <ActivityIndicator size="large" color={colors.accent} />
        </View>
      ) : (
        <View style={styles.tableContainer}>
          <View style={styles.tableHeader}>
            <Text style={[styles.headerCell, styles.colSeverity]}>Severity</Text>
            <Text style={[styles.headerCell, styles.colStatus]}>Status</Text>
            <Text style={[styles.headerCell, styles.colCategory]}>Category & Location</Text>
            <Text style={[styles.headerCell, styles.colTime]}>Elapsed Time</Text>
            <View style={styles.colAction} />
          </View>
          
          <FlatList
            data={items}
            keyExtractor={(i) => i.incident_id}
            renderItem={renderItem}
            contentContainerStyle={styles.listContent}
            ListEmptyComponent={() => (
              <View style={styles.emptyBox}>
                <Text style={styles.emptyText}>No incidents require review right now.</Text>
              </View>
            )}
          />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: spacing.xl,
    maxWidth: 1200,
    width: '100%',
    alignSelf: 'center',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.lg,
  },
  title: {
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.xl,
    fontWeight: typography.weights.bold as any,
    color: colors.navy,
  },
  refreshBtn: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
  },
  refreshText: {
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.sm,
    color: colors.navyMid,
  },
  errorBox: {
    backgroundColor: colors.criticalBg,
    padding: spacing.md,
    borderRadius: radius.md,
    marginBottom: spacing.md,
  },
  errorText: { color: colors.critical, fontFamily: typography.fontFamily },
  centerBox: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  tableContainer: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    boxShadow: shadows.sm,
    flex: 1,
    overflow: 'hidden',
  },
  tableHeader: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.offWhite,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
  },
  headerCell: {
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.bold as any,
    color: colors.slate,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  listContent: {
    flexGrow: 1,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.lg,
    paddingHorizontal: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  rowUrgent: {
    backgroundColor: '#fffcf7', // subtle urgent tint
  },
  colSeverity: { flex: 1.5, minWidth: 120 },
  colStatus: { flex: 1.5, minWidth: 140 },
  colCategory: { flex: 3 },
  colTime: { flex: 2 },
  colAction: { width: 100, alignItems: 'flex-end' },
  textMain: {
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium as any,
    color: colors.navyLight,
    textTransform: 'capitalize',
  },
  textSub: {
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.sm,
    color: colors.slate,
    marginTop: 2,
  },
  textEscalated: {
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.bold as any,
    color: colors.critical,
    marginTop: 4,
    textTransform: 'uppercase',
  },
  actionText: {
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.semibold as any,
    color: colors.accent,
  },
  emptyBox: {
    padding: spacing.xxl,
    alignItems: 'center',
  },
  emptyText: {
    fontFamily: typography.fontFamily,
    color: colors.slate,
    fontStyle: 'italic',
  },
});
