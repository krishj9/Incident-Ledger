import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, TextInput, Platform } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useApi } from '../../src/hooks/useApi';
import { SeverityBadge } from '../../src/components/SeverityBadge';
import { StatusBadge } from '../../src/components/StatusBadge';
import { RedlineViewer } from '../../src/components/RedlineViewer';
import { Modal } from '../../src/components/Modal';
import { colors, spacing, radius, typography, shadows } from '../../src/tokens';

// Define explicit interfaces to match API output, bypassing OpenAPI client `any` type limitations
interface VersionDetail {
  id: string;
  version_number: number;
  version_kind: string;
  rendered_narrative: string;
  edit_reason?: string;
  created_at: string;
}

interface IncidentDetail {
  id: string;
  status: string;
  category: string;
  current_severity: string;
  staff_selected_severity: string;
  event_time: string;
  location: string;
  original_factual_notes: string;
  rendered_narrative: string;
  restricted: boolean;
  versions: VersionDetail[];
}

export default function IncidentReviewScreen() {
  const { id } = useLocalSearchParams();
  const router = useRouter();
  const api = useApi();
  
  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [activeModal, setActiveModal] = useState<'edit' | 'changes' | 'severity' | 'approve' | 'addendum' | null>(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  // Form states
  const [editReason, setEditReason] = useState('');
  const [editNarrative, setEditNarrative] = useState('');
  const [changesReason, setChangesReason] = useState('');
  const [newSeverity, setNewSeverity] = useState('high');
  const [severityReason, setSeverityReason] = useState('');
  const [addendumContent, setAddendumContent] = useState('');

  const fetchIncident = async () => {
    try {
      setLoading(true);
      const res = await api.getIncident(id as string) as any;
      setIncident(res as IncidentDetail);
      setEditNarrative(res.rendered_narrative || '');
      setError(null);
    } catch (err) {
      console.error(err);
      setError('Failed to load incident details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncident();
  }, [id]);

  const handleAction = async (action: () => Promise<any>) => {
    setModalLoading(true);
    setModalError(null);
    try {
      await action();
      setActiveModal(null);
      fetchIncident(); // Refresh
    } catch (err: any) {
      setModalError(err.body?.detail?.[0]?.msg || err.body?.detail || 'Action failed.');
    } finally {
      setModalLoading(false);
    }
  };

  if (loading || !incident) {
    return (
      <View style={styles.centerBox}>
        {error ? <Text style={styles.errorText}>{error}</Text> : <ActivityIndicator size="large" color={colors.accent} />}
      </View>
    );
  }

  const { status, current_severity } = incident;

  return (
    <View style={styles.container}>
      <View style={styles.topBar}>
        <TouchableOpacity onPress={() => router.push('/(tabs)/queue')} style={styles.backBtn}>
          <Text style={styles.backText}>← Back to Queue</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.scrollArea} contentContainerStyle={styles.content}>
        
        {/* Header Section */}
        <View style={styles.card}>
          <View style={styles.headerRow}>
            <View>
              <Text style={styles.categoryTitle}>{incident.category.replace(/_/g, ' ')}</Text>
              <Text style={styles.metaText}>{new Date(incident.event_time).toLocaleString()} • {incident.location}</Text>
            </View>
            <View style={styles.badges}>
              <SeverityBadge level={current_severity} />
              <StatusBadge status={status} />
            </View>
          </View>
        </View>

        {/* Action Bar */}
        <View style={styles.actionBar}>
          {status === 'submitted' && (
            <TouchableOpacity style={styles.btnPrimary} onPress={() => handleAction(() => api.acknowledgeReview(incident.id))}>
              <Text style={styles.btnPrimaryText}>Acknowledge Review</Text>
            </TouchableOpacity>
          )}

          {status === 'under_review' && (
            <>
              <TouchableOpacity style={styles.btnOutline} onPress={() => { setEditReason(''); setActiveModal('edit'); }}>
                <Text style={styles.btnOutlineText}>Edit Narrative</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.btnOutline} onPress={() => { setChangesReason(''); setActiveModal('changes'); }}>
                <Text style={styles.btnOutlineText}>Request Changes</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.btnOutline} onPress={() => { setSeverityReason(''); setNewSeverity(current_severity); setActiveModal('severity'); }}>
                <Text style={styles.btnOutlineText}>Change Severity</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.btnSuccess} onPress={() => setActiveModal('approve')}>
                <Text style={styles.btnSuccessText}>Approve Incident</Text>
              </TouchableOpacity>
            </>
          )}

          {(status === 'approved' || status === 'guardian_ack_pending') && (
            <TouchableOpacity style={styles.btnOutline} onPress={() => { setAddendumContent(''); setActiveModal('addendum'); }}>
              <Text style={styles.btnOutlineText}>Create Addendum</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Split View for Narrative */}
        <View style={styles.splitLayout}>
          <View style={styles.splitPanel}>
            <Text style={styles.sectionTitle}>Staff Source (Immutable)</Text>
            <View style={styles.narrativeBoxSource}>
              <Text style={styles.narrativeText}>{incident.original_factual_notes || 'No factual notes provided.'}</Text>
            </View>
          </View>
          
          <View style={styles.splitPanel}>
            <Text style={styles.sectionTitle}>Current Narrative</Text>
            <View style={styles.narrativeBoxCurrent}>
              {incident.versions?.some(v => v.version_kind === 'director_edit') ? (
                <RedlineViewer 
                  original={incident.versions.find(v => v.version_kind === 'staff_submission')?.rendered_narrative || ''} 
                  edited={incident.rendered_narrative} 
                  editReason={incident.versions.find(v => v.version_kind === 'director_edit')?.edit_reason || ''} 
                />
              ) : (
                <Text style={styles.narrativeText}>{incident.rendered_narrative}</Text>
              )}
            </View>
          </View>
        </View>

        {/* Version History */}
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Version History</Text>
          {incident.versions?.map(v => (
            <View key={v.id} style={styles.versionRow}>
              <Text style={styles.versionLabel}>v{v.version_number} - {v.version_kind.replace(/_/g, ' ')}</Text>
              <Text style={styles.versionTime}>{new Date(v.created_at).toLocaleString()}</Text>
            </View>
          ))}
        </View>

      </ScrollView>

      {/* Modals */}
      <Modal visible={activeModal === 'edit'} onClose={() => setActiveModal(null)} title="Director Edit" width={800}>
        <Text style={styles.modalHint}>Constraint: Minor edits must be limited to grammar, spelling, formatting, neutrality, or clarity only.</Text>
        <Text style={styles.label}>Narrative</Text>
        <TextInput 
          style={styles.textAreaLg} multiline value={editNarrative} onChangeText={setEditNarrative} 
        />
        <Text style={styles.label}>Reason for edit (Required)</Text>
        <TextInput 
          style={styles.input} value={editReason} onChangeText={setEditReason} placeholder="e.g. Corrected spelling"
        />
        {modalError && <Text style={styles.modalError}>{modalError}</Text>}
        <TouchableOpacity style={styles.btnPrimary} onPress={() => handleAction(() => api.createDirectorEdit(incident.id, editNarrative, editReason))}>
          <Text style={styles.btnPrimaryText}>{modalLoading ? 'Saving...' : 'Save Edit'}</Text>
        </TouchableOpacity>
      </Modal>

      <Modal visible={activeModal === 'changes'} onClose={() => setActiveModal(null)} title="Request Changes">
        <Text style={styles.label}>Reason for requesting changes (Required)</Text>
        <TextInput 
          style={styles.textArea} multiline value={changesReason} onChangeText={setChangesReason} placeholder="Explain what staff needs to clarify..."
        />
        {modalError && <Text style={styles.modalError}>{modalError}</Text>}
        <TouchableOpacity style={styles.btnPrimary} onPress={() => handleAction(() => api.requestChanges(incident.id, changesReason))}>
          <Text style={styles.btnPrimaryText}>{modalLoading ? 'Submitting...' : 'Return to Staff'}</Text>
        </TouchableOpacity>
      </Modal>

      <Modal visible={activeModal === 'severity'} onClose={() => setActiveModal(null)} title="Change Severity">
        <Text style={styles.label}>New Severity Level</Text>
        <View style={styles.severityRow}>
          {['critical', 'high', 'moderate', 'low'].map(s => (
            <TouchableOpacity key={s} style={[styles.sevBtn, newSeverity === s && styles.sevBtnActive]} onPress={() => setNewSeverity(s)}>
              <Text style={[styles.sevBtnText, newSeverity === s && styles.sevBtnTextActive]}>{s.toUpperCase()}</Text>
            </TouchableOpacity>
          ))}
        </View>
        <Text style={styles.label}>Reason for change (Required)</Text>
        <TextInput 
          style={styles.textArea} multiline value={severityReason} onChangeText={setSeverityReason} placeholder="Justification for override..."
        />
        {modalError && <Text style={styles.modalError}>{modalError}</Text>}
        <TouchableOpacity style={styles.btnPrimary} onPress={() => handleAction(() => api.changeSeverity(incident.id, newSeverity, severityReason))}>
          <Text style={styles.btnPrimaryText}>{modalLoading ? 'Saving...' : 'Update Severity'}</Text>
        </TouchableOpacity>
      </Modal>

      <Modal visible={activeModal === 'approve'} onClose={() => setActiveModal(null)} title="Approve Incident">
        <Text style={styles.modalHint}>Approving this incident will freeze the narrative. If this incident is not restricted, it will automatically notify the guardians.</Text>
        {modalError && <Text style={styles.modalError}>{modalError}</Text>}
        <View style={styles.actionRowRight}>
          <TouchableOpacity style={styles.btnOutline} onPress={() => setActiveModal(null)}>
            <Text style={styles.btnOutlineText}>Cancel</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.btnSuccess} onPress={() => handleAction(() => api.approveIncident(incident.id))}>
            <Text style={styles.btnSuccessText}>{modalLoading ? 'Approving...' : 'Confirm Approval'}</Text>
          </TouchableOpacity>
        </View>
      </Modal>

      <Modal visible={activeModal === 'addendum'} onClose={() => setActiveModal(null)} title="Create Addendum">
        <Text style={styles.modalHint}>An addendum will be appended to the approved report. The original approved version remains immutable.</Text>
        <Text style={styles.label}>Addendum Content</Text>
        <TextInput 
          style={styles.textArea} multiline value={addendumContent} onChangeText={setAddendumContent} placeholder="Enter addendum text..."
        />
        {modalError && <Text style={styles.modalError}>{modalError}</Text>}
        <TouchableOpacity style={styles.btnPrimary} onPress={() => handleAction(() => api.createAddendum(incident.id, addendumContent))}>
          <Text style={styles.btnPrimaryText}>{modalLoading ? 'Saving...' : 'Submit Addendum'}</Text>
        </TouchableOpacity>
      </Modal>

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.offWhite },
  centerBox: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  errorText: { color: colors.critical, fontFamily: typography.fontFamily },
  topBar: { paddingHorizontal: spacing.xl, paddingVertical: spacing.md, backgroundColor: colors.surface, borderBottomWidth: 1, borderColor: colors.border },
  backBtn: { paddingVertical: spacing.sm },
  backText: { color: colors.accent, fontFamily: typography.fontFamily, fontWeight: '600' as any },
  scrollArea: { flex: 1 },
  content: { padding: spacing.xl, gap: spacing.lg, maxWidth: 1400, alignSelf: 'center', width: '100%' },
  
  card: { backgroundColor: colors.surface, padding: spacing.xl, borderRadius: radius.lg, boxShadow: shadows.sm as any },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  categoryTitle: { fontFamily: typography.fontFamily, fontSize: typography.sizes.xl, fontWeight: '700' as any, color: colors.navy, textTransform: 'capitalize' },
  metaText: { fontFamily: typography.fontFamily, fontSize: typography.sizes.sm, color: colors.slate, marginTop: spacing.xs },
  badges: { flexDirection: 'row', gap: spacing.sm },

  actionBar: { flexDirection: 'row', gap: spacing.md, flexWrap: 'wrap', backgroundColor: colors.surface, padding: spacing.md, borderRadius: radius.lg, boxShadow: shadows.sm as any },
  btnPrimary: { backgroundColor: colors.accent, paddingHorizontal: spacing.lg, paddingVertical: spacing.md, borderRadius: radius.md, alignItems: 'center' },
  btnPrimaryText: { color: colors.white, fontFamily: typography.fontFamily, fontWeight: '600' as any },
  btnOutline: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderDark, paddingHorizontal: spacing.lg, paddingVertical: spacing.md, borderRadius: radius.md, alignItems: 'center' },
  btnOutlineText: { color: colors.navyLight, fontFamily: typography.fontFamily, fontWeight: '600' as any },
  btnSuccess: { backgroundColor: colors.approved, paddingHorizontal: spacing.lg, paddingVertical: spacing.md, borderRadius: radius.md, alignItems: 'center' },
  btnSuccessText: { color: colors.white, fontFamily: typography.fontFamily, fontWeight: '600' as any },

  splitLayout: { flexDirection: Platform.OS === 'web' && (typeof window !== 'undefined' && window.innerWidth > 768) ? 'row' : 'column', gap: spacing.lg },
  splitPanel: { flex: 1, backgroundColor: colors.surface, borderRadius: radius.lg, padding: spacing.xl, boxShadow: shadows.sm as any },
  sectionTitle: { fontFamily: typography.fontFamily, fontSize: typography.sizes.md, fontWeight: '700' as any, color: colors.navyLight, marginBottom: spacing.md },
  
  narrativeBoxSource: { backgroundColor: '#f8fafc', padding: spacing.lg, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border },
  narrativeBoxCurrent: { backgroundColor: '#fff', padding: spacing.lg, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border },
  narrativeText: { fontFamily: "'Georgia', serif", fontSize: typography.sizes.md, lineHeight: 26, color: colors.navyLight },

  versionRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.border },
  versionLabel: { fontFamily: typography.fontFamily, color: colors.navyLight, fontWeight: '500' as any, textTransform: 'capitalize' },
  versionTime: { fontFamily: typography.fontFamily, color: colors.slate, fontSize: typography.sizes.sm },

  label: { fontFamily: typography.fontFamily, fontWeight: '600' as any, color: colors.navyLight, marginBottom: spacing.sm, marginTop: spacing.lg },
  input: { borderWidth: 1, borderColor: colors.borderDark, borderRadius: radius.md, padding: spacing.md, fontFamily: typography.fontFamily, fontSize: typography.sizes.md },
  textArea: { borderWidth: 1, borderColor: colors.borderDark, borderRadius: radius.md, padding: spacing.md, fontFamily: typography.fontFamily, fontSize: typography.sizes.md, height: 120, textAlignVertical: 'top' },
  textAreaLg: { borderWidth: 1, borderColor: colors.borderDark, borderRadius: radius.md, padding: spacing.md, fontFamily: "'Georgia', serif", fontSize: typography.sizes.md, height: 300, textAlignVertical: 'top', lineHeight: 24 },
  
  modalHint: { fontFamily: typography.fontFamily, color: colors.slate, fontSize: typography.sizes.sm, marginBottom: spacing.md, lineHeight: 20 },
  modalError: { color: colors.critical, fontFamily: typography.fontFamily, marginTop: spacing.md, fontWeight: '500' as any },
  actionRowRight: { flexDirection: 'row', justifyContent: 'flex-end', gap: spacing.md, marginTop: spacing.xl },

  severityRow: { flexDirection: 'row', gap: spacing.sm },
  sevBtn: { flex: 1, paddingVertical: spacing.md, borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, alignItems: 'center' },
  sevBtnActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  sevBtnText: { fontFamily: typography.fontFamily, fontWeight: '600' as any, color: colors.slate },
  sevBtnTextActive: { color: colors.white },
});
