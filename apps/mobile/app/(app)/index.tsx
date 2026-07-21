import React, { useEffect, useState, useCallback } from 'react';
import { FlatList, RefreshControl, View } from 'react-native';
import { YStack, XStack, Text, Card, Spinner, Theme } from 'tamagui';
import { IncidentsApi } from '@incident-ledger/api-client';
import { useAuth } from '../../src/contexts/AuthContext';
import { Activity, AlertTriangle, CheckCircle, FileText, User } from 'lucide-react-native';
import { IncidentResponse, IncidentStatus, SeverityLevel } from '@incident-ledger/api-client/src/generated';
import { format } from 'date-fns';

export default function IncidentsTab() {
  const [incidents, setIncidents] = useState<IncidentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchIncidents = async () => {
    try {
      setError(null);
      const data = await IncidentsApi.listIncidents(undefined, 1, 50);
      setIncidents(data.incidents);
    } catch (err) {
      console.error(err);
      setError('Failed to load incidents');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, []);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchIncidents();
  }, []);

  const renderEmpty = () => {
    if (loading) return null;
    return (
      <YStack flex={1} justifyContent="center" alignItems="center" padding="$6">
        <FileText size={48} color="#9ca3af" />
        <Text color="$colorFocus" marginTop="$4" fontSize="$5">
          {error ? error : 'No incidents yet'}
        </Text>
      </YStack>
    );
  };

  const getSeverityColor = (severity: SeverityLevel) => {
    switch (severity) {
      case 'low': return '$blue10';
      case 'moderate': return '$yellow10';
      case 'high': return '$orange10';
      case 'critical': return '$red10';
      default: return '$gray10';
    }
  };

  const getStatusColor = (status: IncidentStatus) => {
    switch (status) {
      case 'draft': return '$gray10';
      case 'submitted': return '$blue10';
      case 'approved': return '$green10';
      default: return '$orange10';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'injury_accident': return <AlertTriangle size={16} color="#4b5563" />;
      case 'illness_medical': return <Activity size={16} color="#4b5563" />;
      default: return <FileText size={16} color="#4b5563" />;
    }
  };

  const renderItem = ({ item }: { item: IncidentResponse }) => {
    return (
      <YStack backgroundColor="$background" borderColor="$borderColor" borderWidth={1} borderRadius="$4" marginHorizontal="$4" marginVertical="$2" padding="$4" shadowColor="#000" shadowOpacity={0.05} shadowRadius={4} shadowOffset={{ width: 0, height: 2 }}>
        <XStack justifyContent="space-between" alignItems="center" marginBottom="$2">
          <XStack alignItems="center" gap="$2">
            {getCategoryIcon(item.category)}
            <Text fontWeight="600" color="$color" textTransform="capitalize">
              {item.category.replace('_', ' ')}
            </Text>
          </XStack>
          <Text fontSize="$2" color="$colorFocus">
            {format(new Date(item.created_at), 'MMM d, yyyy')}
          </Text>
        </XStack>

        <YStack gap="$2" marginTop="$2">
          {item.first_child_name ? (
            <XStack alignItems="center" gap="$2">
              <User size={14} color="#6b7280" />
              <Text fontSize="$3" color="$colorFocus">{item.first_child_name}</Text>
            </XStack>
          ) : null}

          <XStack gap="$2" flexWrap="wrap" marginTop="$2">
            <View style={{ backgroundColor: getSeverityColor(item.severity).replace('10', '4'), paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12 }}>
              <Text fontSize="$2" fontWeight="600" textTransform="uppercase" color={getSeverityColor(item.severity)}>
                {item.severity}
              </Text>
            </View>
            <View style={{ backgroundColor: getStatusColor(item.status).replace('10', '4'), paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12 }}>
              <Text fontSize="$2" fontWeight="600" textTransform="uppercase" color={getStatusColor(item.status)}>
                {item.status.replace('_', ' ')}
              </Text>
            </View>
          </XStack>
        </YStack>
      </YStack>
    );
  };

  if (loading && !refreshing) {
    return (
      <YStack flex={1} justifyContent="center" alignItems="center" backgroundColor="$background">
        <Spinner size="large" color="$blue10" />
      </YStack>
    );
  }

  return (
    <YStack flex={1} backgroundColor="$background">
      <FlatList
        data={incidents}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        contentContainerStyle={{ paddingVertical: 16, flexGrow: 1 }}
        ListEmptyComponent={renderEmpty}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      />
    </YStack>
  );
}
