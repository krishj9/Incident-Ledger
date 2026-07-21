import React, { useEffect, useState } from 'react';
import { AuthApi } from '@incident-ledger/api-client';
import * as SecureStore from 'expo-secure-store';
import { useAuth } from '../contexts/AuthContext';
import { User } from 'lucide-react-native';
import { XStack, YStack, Text, Button, Spinner, Tooltip } from 'tamagui';
import { useNetworkState } from '../hooks/useNetworkState';

const PROFILE_CACHE_KEY = 'incident_ledger_profile_cache';

export function ActiveUserBar() {
  const { signOut } = useAuth();
  const [profile, setProfile] = useState<{ display_name: string; role: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const { isOnline } = useNetworkState();

  useEffect(() => {
    async function loadProfile() {
      try {
        const data = await AuthApi.getMe();
        const newProfile = { display_name: data.display_name, role: data.role };
        setProfile(newProfile);
        await SecureStore.setItemAsync(PROFILE_CACHE_KEY, JSON.stringify(newProfile));
      } catch (err) {
        const cached = await SecureStore.getItemAsync(PROFILE_CACHE_KEY);
        if (cached) {
          setProfile(JSON.parse(cached));
        } else {
          setProfile({ display_name: 'DEMO-Alex Kim', role: 'Staff' });
        }
      } finally {
        setLoading(false);
      }
    }
    loadProfile();
  }, []);

  const handleSwitchStaff = async () => {
    await signOut();
  };

  return (
    <XStack
      alignItems="center"
      justifyContent="space-between"
      backgroundColor="$background"
      paddingHorizontal="$4"
      paddingVertical="$3"
      borderBottomWidth={1}
      borderBottomColor="$borderColor"
    >
      <XStack alignItems="center" gap="$2">
        <User size={20} color="#333" />
        {loading ? (
          <Spinner size="small" color="$color" />
        ) : (
          <Text fontSize="$4" fontWeight="600" color="$color">
            {profile ? `${profile.display_name} · ${profile.role}` : 'Unknown User'}
          </Text>
        )}
      </XStack>
      <Tooltip placement="bottom" delay={0}>
        <Tooltip.Trigger asChild>
          <Button 
            size="$3" 
            theme="alt1" 
            onPress={isOnline ? handleSwitchStaff : undefined}
            opacity={isOnline ? 1 : 0.5}
          >
            Switch Staff
          </Button>
        </Tooltip.Trigger>
        <Tooltip.Content>
          <Tooltip.Arrow />
          <Text color="$color">Staff switch requires server confirmation. Connect to the network first.</Text>
        </Tooltip.Content>
      </Tooltip>
    </XStack>
  );
}
