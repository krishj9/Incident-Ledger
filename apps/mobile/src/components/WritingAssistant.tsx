import React, { useState } from 'react';
import { View, Alert } from 'react-native';
import { YStack, XStack, Text, Button, Spinner, Input, Card } from 'tamagui';
import { Sparkles, Check, X, Edit2 } from 'lucide-react-native';
import { WritingApi, SuggestionItem } from '@incident-ledger/api-client';
import * as Crypto from 'expo-crypto';

interface WritingAssistantProps {
  incidentId: string;
  category: string;
  severity: string;
  timePrecision: string;
  eventAt: string;
  location: string;
  witnessesKnown: boolean;
  factualNotes: string;
  actionsTaken: string;
  treatmentResponse: string;
  onApplySuggestion: (text: string) => void;
}

export function WritingAssistant({
  incidentId,
  category,
  severity,
  timePrecision,
  eventAt,
  location,
  witnessesKnown,
  factualNotes,
  actionsTaken,
  treatmentResponse,
  onApplySuggestion,
}: WritingAssistantProps) {
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  
  // Track metadata for disposition telemetry
  const [modelVersion, setModelVersion] = useState<string>('');
  const [promptVersion, setPromptVersion] = useState<string>('');

  const fetchSuggestions = async () => {
    if (!factualNotes || !actionsTaken) {
      Alert.alert('Not enough information', 'Please fill out factual notes and actions taken first.');
      return;
    }
    
    setLoading(true);
    try {
      const response = await WritingApi.getSuggestions({
        category,
        severity,
        event_time_precision: timePrecision,
        event_at: eventAt,
        location,
        witnesses_known: witnessesKnown,
        original_factual_notes: factualNotes,
        actions_taken: actionsTaken,
        treatment_response: treatmentResponse
      });
      
      if (!response.available) {
        Alert.alert('Assistant Unavailable', response.reason || 'Could not fetch suggestions.');
        return;
      }
      
      setSuggestions(response.suggestions || []);
      setModelVersion(response.model_version || '');
      setPromptVersion(response.prompt_version || '');
      
    } catch (e) {
      Alert.alert('Error', 'Failed to fetch writing suggestions.');
      console.error(e);
    } finally {
      setLoading(false);
    }
  };
  
  const recordDisposition = async (suggestion: SuggestionItem, disposition: 'accepted' | 'rejected' | 'edited', text?: string) => {
    try {
      await WritingApi.recordDisposition(incidentId, suggestion.id, {
        suggestion_type: suggestion.type,
        disposition,
        edited_text: text,
        model_version: modelVersion,
        prompt_version: promptVersion,
        field_hashes: {} // In a real app we'd hash the current fields for audit
      });
    } catch (e) {
      // Telemetry failure shouldn't block the user, just log it
      console.warn('Failed to record disposition telemetry', e);
    }
  };

  const handleAccept = (suggestion: SuggestionItem) => {
    if (suggestion.proposed_text) {
      onApplySuggestion(suggestion.proposed_text);
    }
    recordDisposition(suggestion, 'accepted');
    removeSuggestion(suggestion.id);
  };

  const handleReject = (suggestion: SuggestionItem) => {
    recordDisposition(suggestion, 'rejected');
    removeSuggestion(suggestion.id);
  };

  const startEdit = (suggestion: SuggestionItem) => {
    setEditingId(suggestion.id);
    setEditText(suggestion.proposed_text || '');
  };

  const submitEdit = (suggestion: SuggestionItem) => {
    if (editText) {
      onApplySuggestion(editText);
      recordDisposition(suggestion, 'edited', editText);
    }
    setEditingId(null);
    removeSuggestion(suggestion.id);
  };

  const removeSuggestion = (id: string) => {
    setSuggestions(prev => prev.filter(s => s.id !== id));
  };

  // If the category is restricted, don't even show the CTA
  if (category === 'suspected_abuse_neglect') {
    return null;
  }

  return (
    <YStack gap="$3" marginTop="$4">
      {suggestions.length === 0 && (
        <Button 
          theme="alt2" 
          icon={loading ? <Spinner /> : Sparkles} 
          onPress={fetchSuggestions}
          disabled={loading}
        >
          {loading ? 'Analyzing...' : 'Get Writing Suggestions'}
        </Button>
      )}

      {suggestions.length > 0 && (
        <YStack gap="$3">
          <Text fontWeight="bold" fontSize="$4" color="$blue10">AI Suggestions</Text>
          
          {suggestions.map(s => (
            <Card key={s.id} borderWidth={1} padding="$3" theme="blue">
              <YStack gap="$2">
                <Text fontWeight="bold" textTransform="capitalize">{s.type.replace(/_/g, ' ')}</Text>
                <Text color="$colorFocus">{s.rationale}</Text>
                
                {s.question && (
                  <Text fontStyle="italic" marginTop="$2">{s.question}</Text>
                )}
                
                {s.proposed_text && !editingId && (
                  <YStack backgroundColor="$background" padding="$3" borderRadius="$2" marginTop="$2">
                    <Text>{s.proposed_text}</Text>
                    <XStack gap="$2" marginTop="$3" justifyContent="flex-end">
                      <Button size="$2" theme="active" icon={Check} onPress={() => handleAccept(s)}>Accept</Button>
                      <Button size="$2" theme="alt1" icon={Edit2} onPress={() => startEdit(s)}>Edit</Button>
                      <Button size="$2" theme="red" icon={X} onPress={() => handleReject(s)}>Reject</Button>
                    </XStack>
                  </YStack>
                )}
                
                {editingId === s.id && (
                  <YStack marginTop="$2" gap="$2">
                    <Input value={editText} onChangeText={setEditText} multiline minHeight={80} />
                    <XStack gap="$2" justifyContent="flex-end">
                      <Button size="$2" theme="alt1" onPress={() => setEditingId(null)}>Cancel</Button>
                      <Button size="$2" theme="active" icon={Check} onPress={() => submitEdit(s)}>Apply Edit</Button>
                    </XStack>
                  </YStack>
                )}
                
                {!s.proposed_text && (
                  <XStack gap="$2" marginTop="$3" justifyContent="flex-end">
                    <Button size="$2" theme="red" onPress={() => handleReject(s)}>Dismiss</Button>
                  </XStack>
                )}
              </YStack>
            </Card>
          ))}
        </YStack>
      )}
    </YStack>
  );
}
