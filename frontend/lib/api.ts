const API_BASE = "http://localhost:8000";

export type ExtractedJson = {
  patient_info: {
    name: string;
    age: string;
    sex: string;
    visit_date: string;
    doctor_name: string;
  };
  diagnoses: string[];
  medications: Array<{
    name: string;
    dose: string;
    frequency: string;
    timing: string;
    duration: string;
    warnings: string;
  }>;
  tests: Array<{
    test_name: string;
    result: string;
    interpretation: string;
  }>;
  follow_up: string[];
  red_flags: string[];
  doctor_instructions: string[];
};

export type UploadAndExtractResponse = {
  session_id: string;
  filename: string;
  extracted: ExtractedJson;
};

export async function uploadAndExtract(
  file: File
): Promise<UploadAndExtractResponse> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE}/upload-and-extract`, {
    method: "POST",
    body: form,
  });

  const text = await res.text();
  let data: unknown;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(text || "Invalid response from server");
  }

  if (!res.ok) {
    let detail = text || `Request failed (${res.status})`;
    if (typeof data === "object" && data !== null && "detail" in data) {
      const d = (data as { detail: unknown }).detail;
      if (typeof d === "string") detail = d;
      else if (Array.isArray(d))
        detail = d
          .map((e) => (typeof e === "object" && e && "msg" in e ? String((e as { msg: unknown }).msg) : String(e)))
          .join("; ");
    }
    throw new Error(detail);
  }

  return data as UploadAndExtractResponse;
}

export async function askSession(
  sessionId: string,
  question: string
): Promise<{ answer: string }> {
  const res = await fetch(`${API_BASE}/sessions/${encodeURIComponent(sessionId)}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  const text = await res.text();
  let data: unknown;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(text || "Invalid response from server");
  }

  if (!res.ok) {
    let detail = text || `Request failed (${res.status})`;
    if (typeof data === "object" && data !== null && "detail" in data) {
      const d = (data as { detail: unknown }).detail;
      if (typeof d === "string") detail = d;
      else if (Array.isArray(d))
        detail = d
          .map((e) => (typeof e === "object" && e && "msg" in e ? String((e as { msg: unknown }).msg) : String(e)))
          .join("; ");
    }
    throw new Error(detail);
  }

  return data as { answer: string };
}
