import { useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { View, Text, StyleSheet, ActivityIndicator, TextInput, TouchableOpacity, ScrollView } from "react-native";
import { fetchAcknowledgement, submitAcknowledgement, AcknowledgementData } from "../api";

export default function AcknowledgeScreen() {
  const { token } = useLocalSearchParams<{ token: string }>();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<AcknowledgementData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [typedName, setTypedName] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [disagreementComment, setDisagreementComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [outcome, setOutcome] = useState<"acknowledged" | "disagreed" | null>(null);

  useEffect(() => {
    if (!token) return;
    fetchAcknowledgement(token)
      .then((res) => {
        setData(res);
        if (res.acknowledgement_status !== "sent" && res.acknowledgement_status !== "pending") {
           setError("This link is no longer valid.");
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  const handleSubmit = async (selectedOutcome: "acknowledged" | "disagreed") => {
    if (!token || !typedName.trim()) return;
    if (selectedOutcome === "acknowledged" && !confirmed) return;
    
    setSubmitting(true);
    setOutcome(selectedOutcome);
    
    try {
      await submitAcknowledgement(token, selectedOutcome, typedName.trim(), disagreementComment);
      setSubmitted(true);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#0066cc" />
      </View>
    );
  }

  if (error || !data) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorTitle}>Error</Text>
        <Text style={styles.errorText}>{error || "This link is no longer valid."}</Text>
      </View>
    );
  }

  if (submitted) {
    return (
      <View style={styles.center}>
        <Text style={styles.successTitle}>Thank You</Text>
        <Text style={styles.successText}>Your response has been successfully recorded.</Text>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.card}>
        <Text style={styles.title}>Incident Report</Text>
        
        <View style={styles.infoRow}>
          <Text style={styles.label}>Child:</Text>
          <Text style={styles.value}>{data.child_name}</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.label}>Date:</Text>
          <Text style={styles.value}>{new Date(data.incident_date).toLocaleString()}</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.label}>Category:</Text>
          <Text style={styles.value}>{data.incident_category}</Text>
        </View>

        <Text style={styles.sectionTitle}>Narrative</Text>
        <Text style={styles.narrative}>{data.approved_narrative}</Text>

        {data.child_details && (
          <>
            <Text style={styles.sectionTitle}>Child-Specific Details</Text>
            <Text style={styles.narrative}>{data.child_details}</Text>
          </>
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.title}>Acknowledgement</Text>
        
        <Text style={styles.label}>Electronic Signature (Type Full Name)*</Text>
        <TextInput
          style={styles.input}
          placeholder="e.g. Jane Doe"
          value={typedName}
          onChangeText={setTypedName}
        />

        <TouchableOpacity 
          style={styles.checkboxContainer}
          onPress={() => setConfirmed(!confirmed)}
        >
          <View style={[styles.checkbox, confirmed && styles.checkboxChecked]} />
          <Text style={styles.checkboxLabel}>I confirm I have received and read this incident report.</Text>
        </TouchableOpacity>

        <TouchableOpacity 
          style={[styles.button, styles.btnPrimary, (!confirmed || !typedName.trim() || submitting) && styles.btnDisabled]}
          onPress={() => handleSubmit("acknowledged")}
          disabled={!confirmed || !typedName.trim() || submitting}
        >
          <Text style={styles.btnText}>{submitting && outcome === "acknowledged" ? "Submitting..." : "Acknowledge"}</Text>
        </TouchableOpacity>

        <Text style={styles.orText}>OR</Text>
        
        <Text style={styles.label}>Reason for Disagreement (Optional)</Text>
        <TextInput
          style={[styles.input, styles.textArea]}
          placeholder="State your concerns here..."
          value={disagreementComment}
          onChangeText={setDisagreementComment}
          multiline
        />
        
        <TouchableOpacity 
          style={[styles.button, styles.btnSecondary, (!typedName.trim() || submitting) && styles.btnDisabled]}
          onPress={() => handleSubmit("disagreed")}
          disabled={!typedName.trim() || submitting}
        >
          <Text style={[styles.btnText, styles.btnSecondaryText]}>
            {submitting && outcome === "disagreed" ? "Submitting..." : "I Disagree"}
          </Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: "center", alignItems: "center", padding: 20 },
  container: { padding: 20, maxWidth: 600, width: "100%", alignSelf: "center" },
  card: {
    backgroundColor: "#fff",
    borderRadius: 8,
    padding: 20,
    marginBottom: 20,
    shadowColor: "#000",
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
    borderWidth: 1,
    borderColor: "#eaeaea"
  },
  title: { fontSize: 24, fontWeight: "700", marginBottom: 16, color: "#333" },
  infoRow: { flexDirection: "row", marginBottom: 8 },
  label: { fontWeight: "600", width: 80, color: "#555" },
  value: { flex: 1, color: "#333" },
  sectionTitle: { fontSize: 18, fontWeight: "600", marginTop: 16, marginBottom: 8, color: "#444" },
  narrative: { fontSize: 15, lineHeight: 22, color: "#444", backgroundColor: "#f9f9f9", padding: 12, borderRadius: 6 },
  input: {
    borderWidth: 1,
    borderColor: "#ccc",
    borderRadius: 6,
    padding: 12,
    fontSize: 16,
    marginTop: 8,
    marginBottom: 16,
    backgroundColor: "#fff"
  },
  textArea: { minHeight: 80, textAlignVertical: "top" },
  checkboxContainer: { flexDirection: "row", alignItems: "center", marginBottom: 20 },
  checkbox: {
    width: 24, height: 24, borderRadius: 4, borderWidth: 2, borderColor: "#0066cc", marginRight: 12,
    backgroundColor: "#fff"
  },
  checkboxChecked: { backgroundColor: "#0066cc" },
  checkboxLabel: { flex: 1, fontSize: 15, color: "#333" },
  button: {
    padding: 16, borderRadius: 8, alignItems: "center", justifyContent: "center"
  },
  btnPrimary: { backgroundColor: "#0066cc" },
  btnSecondary: { backgroundColor: "#fff", borderWidth: 1, borderColor: "#d9534f" },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  btnSecondaryText: { color: "#d9534f" },
  orText: { textAlign: "center", marginVertical: 16, color: "#888", fontWeight: "600" },
  errorTitle: { fontSize: 24, fontWeight: "bold", color: "#d9534f", marginBottom: 8 },
  errorText: { fontSize: 16, color: "#555", textAlign: "center" },
  successTitle: { fontSize: 24, fontWeight: "bold", color: "#28a745", marginBottom: 8 },
  successText: { fontSize: 16, color: "#555", textAlign: "center" }
});
