import React, { useState } from 'react';
import { useAuth } from '../../src/contexts/AuthContext';
import { useRouter } from 'expo-router';
import { YStack, Text, Button, Spinner } from 'tamagui';

export default function SignInScreen() {
  const { signIn } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleMockSignIn = async () => {
    setLoading(true);
    setError(null);
    try {
      await signIn('mock_demo_token');
      router.replace('/(app)');
    } catch (err) {
      setError('Failed to sign in. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleEntraSignIn = async () => {
    console.log('Entra sign-in not yet fully implemented, using Mock Auth for now.');
    handleMockSignIn();
  };

  return (
    <YStack flex={1} justifyContent="center" alignItems="center" padding="$6" backgroundColor="$background">
      <Text fontSize="$8" fontWeight="bold" color="$color" marginBottom="$2">
        Incident Ledger
      </Text>
      <Text fontSize="$5" color="$colorFocus" marginBottom="$8">
        Staff Mobile App
      </Text>

      {error ? (
        <Text color="$red10" marginBottom="$4">
          {error}
        </Text>
      ) : null}

      <Button
        size="$5"
        theme="active"
        width="100%"
        onPress={handleEntraSignIn}
        disabled={loading}
        icon={loading ? () => <Spinner color="$color" /> : undefined}
      >
        Sign in with Microsoft
      </Button>
    </YStack>
  );
}
