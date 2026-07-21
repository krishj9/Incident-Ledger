const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000";

export interface AcknowledgementData {
  child_name: string;
  incident_date: string;
  incident_category: string;
  approved_narrative: string;
  child_details: string | null;
  acknowledgement_status: string;
}

export async function fetchAcknowledgement(token: string): Promise<AcknowledgementData> {
  const response = await fetch(`${API_BASE_URL}/v1/guardian/acknowledgements/${token}`);
  
  if (!response.ok) {
    if (response.status === 404 || response.status === 401 || response.status === 403) {
      throw new Error("This link is no longer valid.");
    }
    throw new Error("An unexpected error occurred.");
  }
  
  return response.json();
}

export async function submitAcknowledgement(
  token: string, 
  outcome: "acknowledged" | "disagreed", 
  typedFullName: string,
  disagreementComment?: string
) {
  const response = await fetch(`${API_BASE_URL}/v1/guardian/acknowledgements/${token}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      outcome,
      typed_full_name: typedFullName,
      disagreement_comment: disagreementComment,
    })
  });
  
  if (!response.ok) {
    throw new Error("Failed to submit acknowledgement.");
  }
  
  return response.json();
}
