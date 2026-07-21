import React, { useState, useEffect } from 'react';
import { ScrollView, Alert, Platform, View } from 'react-native';
import { YStack, XStack, Text, Button, Input, TextArea, Checkbox, Switch, Spinner, Label, RadioGroup } from 'tamagui';
import { ChevronLeft, ChevronRight, Save, Check, Cloud, CloudOff } from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { ChildrenApi, ChildResponse } from '@incident-ledger/api-client';
import DateTimePicker from '@react-native-community/datetimepicker';
import { useDraftPersistence } from '../../src/hooks/useDraftPersistence';
import { useNetworkState } from '../../src/hooks/useNetworkState';
import { getLocalEvidence, LocalEvidence } from '../../src/db';
import { Camera } from 'lucide-react-native';
import { Image } from 'react-native';
import { WritingAssistant } from '../../src/components/WritingAssistant';

export default function NewReportWizard() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [childrenList, setChildrenList] = useState<ChildResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showDatePicker, setShowDatePicker] = useState(false);

  const { isOnline } = useNetworkState();
  
  // Local UI state mapped to draft fields
  const [selectedChildren, setSelectedChildren] = useState<Record<string, 'primary_affected' | 'involved' | 'witness'>>({});
  const [category, setCategory] = useState<string>('');
  const [severity, setSeverity] = useState<string>('');
  const [eventAt, setEventAt] = useState<Date>(new Date());
  const [timePrecision, setTimePrecision] = useState<'exact' | 'estimated'>('exact');
  const [location, setLocation] = useState('');
  
  const [factualNotes, setFactualNotes] = useState('');
  const [actionsTaken, setActionsTaken] = useState('');
  const [treatmentResponse, setTreatmentResponse] = useState('');
  const [witnessesPresent, setWitnessesPresent] = useState(false);
  const [attestation, setAttestation] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const [evidenceList, setEvidenceList] = useState<LocalEvidence[]>([]);
  const { draftId, saveStatus, isHydrating, updateDraftFields, saveExplicitly, submitDraft } = useDraftPersistence();

  // Load evidence whenever step 4 is active
  useEffect(() => {
    if (step === 4) {
      getLocalEvidence(draftId).then(setEvidenceList).catch(console.error);
    }
  }, [step, draftId]);

  useEffect(() => {
    const fetchChildren = async () => {
      try {
        const response = await ChildrenApi.listChildren();
        setChildrenList(response.children);
      } catch (e) {
        console.error('Failed to load child roster', e);
        // We could load cached_roster here offline
      } finally {
        setLoading(false);
      }
    };
    fetchChildren();
  }, []);

  // Sync UI state changes to local SQLite (debounced inside hook)
  useEffect(() => {
    if (isHydrating) return;
    updateDraftFields({
      children: Object.entries(selectedChildren).map(([id, role]) => ({ child_id: id, role })),
      category,
      severity,
      event_at: eventAt.toISOString(),
      event_time_precision: timePrecision,
      location,
      original_factual_notes: factualNotes,
      actions_taken: actionsTaken,
      treatment_response: treatmentResponse,
      witnesses_known: witnessesPresent,
    });
  }, [selectedChildren, category, severity, eventAt, timePrecision, location, factualNotes, actionsTaken, treatmentResponse, witnessesPresent, isHydrating]);

  const hasPrimaryAffected = Object.values(selectedChildren).includes('primary_affected');

  const handleNext = () => {
    if (step === 1 && !hasPrimaryAffected) {
      Alert.alert('Validation', 'Must select exactly one primary affected child.');
      return;
    }
    if (step === 2 && (!category || !severity || !location)) {
      Alert.alert('Validation', 'Please fill in all required fields (Category, Severity, Location).');
      return;
    }
    if (step === 3 && (!factualNotes || !actionsTaken)) {
      Alert.alert('Validation', 'Please provide factual notes and actions taken.');
      return;
    }
    setStep((s) => Math.min(4, s + 1));
  };

  const handleBack = () => {
    setStep((s) => Math.max(1, s - 1));
  };

  const toggleChildRole = (childId: string, role: 'primary_affected' | 'involved' | 'witness') => {
    setSelectedChildren(prev => {
      const next = { ...prev };
      if (next[childId] === role) {
        delete next[childId];
      } else {
        if (role === 'primary_affected') {
          Object.keys(next).forEach(k => {
            if (next[k] === 'primary_affected') delete next[k];
          });
        }
        next[childId] = role;
      }
      return next;
    });
  };

  const onSaveDraft = async () => {
    try {
      await saveExplicitly();
    } catch (e) {
      Alert.alert('Error', 'Failed to save draft locally.');
    }
  };

  const onSubmit = async () => {
    if (!attestation) {
      Alert.alert('Validation', 'You must confirm the report is accurate to submit.');
      return;
    }
    setIsSubmitting(true);
    try {
      await submitDraft(
        { accurate_to_best_of_knowledge: true, confirmed_at: new Date().toISOString() },
        { device_id: '00000000-0000-0000-0000-000000000000', offline_originated: !isOnline }
      );
      
      const successMessage = isOnline ? 'Incident report submitted successfully!' : 'Submitted—pending secure sync';
      Alert.alert('Success', successMessage, [
        { text: 'OK', onPress: () => router.push('/') }
      ]);
    } catch (e) {
      Alert.alert('Error', 'Failed to submit report.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading || isHydrating) {
    return <YStack flex={1} justifyContent="center" alignItems="center"><Spinner size="large" /></YStack>;
  }

  return (
    <YStack flex={1} backgroundColor="$background">
      {/* Progress & Status Header */}
      <XStack padding="$4" backgroundColor="$background" borderBottomWidth={1} borderColor="$borderColor" alignItems="center" justifyContent="space-between">
        <YStack>
          <Text fontWeight="bold" fontSize="$5">Step {step} of 4</Text>
          <XStack alignItems="center" gap="$2" marginTop="$1">
            {isOnline ? <Cloud size={14} color="#10b981" /> : <CloudOff size={14} color="#ef4444" />}
            <Text fontSize="$2" color="$colorFocus">{saveStatus || 'Drafting...'}</Text>
          </XStack>
        </YStack>
        <Button size="$3" theme="alt1" icon={Save} onPress={onSaveDraft} disabled={isSubmitting}>Save</Button>
      </XStack>

      <ScrollView contentContainerStyle={{ padding: 16 }}>
        {step === 1 && (
          <YStack gap="$4">
            <Text fontSize="$6" fontWeight="bold">Select Children</Text>
            <Text color="$colorFocus">Select the primary affected child and any other involved children or witnesses.</Text>
            {childrenList.length === 0 ? <Text>No children found.</Text> : null}
            {childrenList.map(child => (
              <YStack key={child.id} padding="$3" borderWidth={1} borderColor="$borderColor" borderRadius="$4" gap="$2">
                <Text fontWeight="bold">{child.display_name}</Text>
                <XStack gap="$2" flexWrap="wrap">
                  <Button size="$2" theme={selectedChildren[child.id] === 'primary_affected' ? 'active' : 'alt1'} onPress={() => toggleChildRole(child.id, 'primary_affected')}>Primary</Button>
                  <Button size="$2" theme={selectedChildren[child.id] === 'involved' ? 'active' : 'alt1'} onPress={() => toggleChildRole(child.id, 'involved')}>Involved</Button>
                  <Button size="$2" theme={selectedChildren[child.id] === 'witness' ? 'active' : 'alt1'} onPress={() => toggleChildRole(child.id, 'witness')}>Witness</Button>
                </XStack>
              </YStack>
            ))}
          </YStack>
        )}

        {step === 2 && (
          <YStack gap="$4">
            <Text fontSize="$6" fontWeight="bold">Event Details</Text>
            
            <Label>Category</Label>
            <RadioGroup value={category} onValueChange={setCategory}>
              {['injury_accident', 'illness_medical', 'behavioral', 'suspected_abuse_neglect', 'missing_child', 'medication_error', 'property_damage', 'other'].map(cat => (
                <XStack key={cat} alignItems="center" gap="$2" marginBottom="$2">
                  <RadioGroup.Item value={cat} id={`cat-${cat}`}>
                    <RadioGroup.Indicator />
                  </RadioGroup.Item>
                  <Label htmlFor={`cat-${cat}`} textTransform="capitalize">{cat.replace(/_/g, ' ')}</Label>
                </XStack>
              ))}
            </RadioGroup>

            {category === 'suspected_abuse_neglect' && (
              <YStack backgroundColor="$red2" padding="$3" borderRadius="$4" borderWidth={1} borderColor="$red6">
                <Text color="$red10" fontWeight="bold">Restriction Notice</Text>
                <Text color="$red10">This report will be restricted. AI writing assistance will not be available.</Text>
              </YStack>
            )}

            <Label>Severity</Label>
            <XStack gap="$2" flexWrap="wrap">
              {['low', 'moderate', 'high', 'critical'].map(sev => (
                <Button key={sev} size="$3" theme={severity === sev ? 'active' : 'alt1'} onPress={() => setSeverity(sev)}>{sev}</Button>
              ))}
            </XStack>

            <Label>Event Date/Time</Label>
            <XStack gap="$2" alignItems="center">
              <Button onPress={() => setShowDatePicker(true)}>{eventAt.toLocaleString()}</Button>
              {showDatePicker && (
                <DateTimePicker
                  value={eventAt}
                  mode="datetime"
                  display="default"
                  onChange={(event, date) => {
                    setShowDatePicker(Platform.OS === 'ios');
                    if (date) setEventAt(date);
                  }}
                />
              )}
            </XStack>

            <Label>Time Precision</Label>
            <XStack gap="$2">
              <Button size="$3" theme={timePrecision === 'exact' ? 'active' : 'alt1'} onPress={() => setTimePrecision('exact')}>Exact</Button>
              <Button size="$3" theme={timePrecision === 'estimated' ? 'active' : 'alt1'} onPress={() => setTimePrecision('estimated')}>Estimated</Button>
            </XStack>

            <Label>Location</Label>
            <Input value={location} onChangeText={setLocation} placeholder="e.g. Playground" />
          </YStack>
        )}

        {step === 3 && (
          <YStack gap="$4">
            <Text fontSize="$6" fontWeight="bold">Description</Text>
            
            <Label>Factual Notes</Label>
            <TextArea value={factualNotes} onChangeText={setFactualNotes} placeholder="Describe exactly what was observed..." minHeight={100} />

            <Label>Actions Taken</Label>
            <TextArea value={actionsTaken} onChangeText={setActionsTaken} placeholder="What did staff do immediately after?" minHeight={80} />

            <Label>Treatment / Response (Optional)</Label>
            <TextArea value={treatmentResponse} onChangeText={setTreatmentResponse} placeholder="First aid or medical response..." minHeight={80} />

            <XStack alignItems="center" gap="$2" marginTop="$2">
              <Switch size="$3" checked={witnessesPresent} onCheckedChange={setWitnessesPresent}>
                <Switch.Thumb />
              </Switch>
              <Label>Were witnesses present?</Label>
            </XStack>
            {!witnessesPresent && (
              <Text color="$colorFocus" fontSize="$3">Confirmed no known witnesses.</Text>
            )}

            <WritingAssistant 
              incidentId={draftId}
              category={category}
              severity={severity}
              timePrecision={timePrecision}
              eventAt={eventAt.toISOString()}
              location={location}
              witnessesKnown={witnessesPresent}
              factualNotes={factualNotes}
              actionsTaken={actionsTaken}
              treatmentResponse={treatmentResponse}
              onApplySuggestion={(text) => {
                // If it's a clarification/edit, maybe we just append or replace
                // Simple append for this implementation demo
                setFactualNotes(prev => prev + (prev ? '\n\n' : '') + text);
              }}
            />
          </YStack>
        )}

        {step === 4 && (
          <YStack gap="$4">
            <Text fontSize="$6" fontWeight="bold">Review & Submit</Text>
            
            <YStack padding="$3" backgroundColor="$gray2" borderRadius="$4">
              <Text fontWeight="bold">Category:</Text>
              <Text marginBottom="$2" textTransform="capitalize">{category.replace(/_/g, ' ')}</Text>
              
              <Text fontWeight="bold">Severity:</Text>
              <Text marginBottom="$2" textTransform="capitalize">{severity}</Text>
              
              <Text fontWeight="bold">Location:</Text>
              <Text marginBottom="$2">{location}</Text>
              
              <Text fontWeight="bold">Primary Affected:</Text>
              <Text marginBottom="$2">
                {childrenList.find(c => selectedChildren[c.id] === 'primary_affected')?.display_name || 'None'}
              </Text>
            </YStack>

            <YStack padding="$3" backgroundColor="$gray2" borderRadius="$4" gap="$3">
              <XStack justifyContent="space-between" alignItems="center">
                <Text fontWeight="bold">Evidence Photos ({evidenceList.length}/5)</Text>
                {(['injury_accident', 'property_damage', 'other'].includes(category)) && evidenceList.length < 5 && (
                  <Button 
                    size="$3" 
                    theme="active" 
                    icon={Camera}
                    onPress={() => router.push({ pathname: '/(app)/evidence-capture', params: { incidentId: draftId, photoCount: evidenceList.length.toString() } })}
                  >
                    Add Photo
                  </Button>
                )}
              </XStack>
              
              {category === 'suspected_abuse_neglect' && (
                <Text color="$red10" fontSize="$3">Photos are disabled for restricted categories.</Text>
              )}

              {evidenceList.length > 0 ? (
                <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                  <XStack gap="$2">
                    {evidenceList.map(ev => (
                      <YStack key={ev.id} position="relative">
                        <Image source={{ uri: ev.local_file_path }} style={{ width: 100, height: 100, borderRadius: 8 }} />
                        <View style={{ position: 'absolute', bottom: 4, right: 4, backgroundColor: 'rgba(0,0,0,0.6)', padding: 4, borderRadius: 4 }}>
                          <Text color="white" fontSize={10}>{ev.upload_status}</Text>
                        </View>
                      </YStack>
                    ))}
                  </XStack>
                </ScrollView>
              ) : (
                <Text color="$colorFocus" fontSize="$3">No photos attached.</Text>
              )}
            </YStack>

            <XStack alignItems="center" gap="$3" marginTop="$4" padding="$2" borderWidth={1} borderColor="$borderColor" borderRadius="$4">
              <Checkbox id="attest" checked={attestation} onCheckedChange={(val) => setAttestation(!!val)}>
                <Checkbox.Indicator><Check /></Checkbox.Indicator>
              </Checkbox>
              <Label htmlFor="attest" flex={1}>I confirm this report is accurate to the best of my knowledge.</Label>
            </XStack>
          </YStack>
        )}

      </ScrollView>

      {/* Footer Navigation */}
      <XStack padding="$4" borderTopWidth={1} borderColor="$borderColor" justifyContent="space-between" backgroundColor="$background">
        <Button size="$4" theme="alt1" icon={ChevronLeft} onPress={handleBack} disabled={step === 1 || isSubmitting}>
          Back
        </Button>
        {step < 4 ? (
          <Button size="$4" theme="active" iconAfter={ChevronRight} onPress={handleNext}>
            Next
          </Button>
        ) : (
          <Button size="$4" theme="active" onPress={onSubmit} disabled={isSubmitting}>
            {isSubmitting ? <Spinner /> : 'Submit'}
          </Button>
        )}
      </XStack>
    </YStack>
  );
}
