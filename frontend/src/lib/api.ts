/**
 * API client for DIP backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Company {
  display_name: string;
  folder_name: string;
}

export interface SmartCard {
  id: string;
  icon: string;
  title: string;
  data_source: string;
}

export interface ChatRequest {
  question: string;
  company_display_name: string;
  company_folder_name: string;
  source: "chat" | "smart_card";
  smart_card_id?: string;
  data_source?: string;
  project_id?: string;
  gcs_bucket?: string;
}

export interface FilesData {
  structured: string[];
  unstructured: string[];
}

export async function fetchCompanies(): Promise<Company[]> {
  const res = await fetch(`${API_BASE}/api/companies`);
  return res.json();
}

export async function fetchSmartCards(folderName: string): Promise<SmartCard[]> {
  const res = await fetch(`${API_BASE}/api/smart-cards?folder_name=${encodeURIComponent(folderName)}`);
  return res.json();
}

export interface CompanyAssets {
  intro_text: string;
  knowledge_text: string;
  knowledge_files: string[];
  prompt_text: string;
  bq: { is_connected: boolean; is_error: boolean; table_count: number; tables: string[]; error_detail: string };
  gcs: { is_connected: boolean; is_error: boolean; file_count: number; files: string[]; error_detail: string };
  local: { structured_files: string[]; unstructured_files: string[] };
}

export async function fetchCompanyAssets(folderName: string, projectId?: string, gcsBucket?: string): Promise<CompanyAssets> {
  const params = new URLSearchParams({ folder_name: folderName });
  params.set("project_id", projectId || "decision-support-ai");
  params.set("gcs_bucket", gcsBucket || "dsa-knowledge-base");
  const res = await fetch(`${API_BASE}/api/company-assets?${params}`);
  return res.json();
}

/**
 * SSEストリーミングでチャットAPIを呼び出す。
 * コールバックでイベントを受信する。
 */
export function streamChat(
  req: ChatRequest,
  callbacks: {
    onText: (text: string) => void;
    onStatus: (message: string, result?: string) => void;
    onFiles: (files: FilesData) => void;
    onFlowSteps: (steps: any[]) => void;
    onDone: (elapsed: number, displayText: string, segments?: any[]) => void;
    onError: (message: string) => void;
  },
): AbortController {
  const controller = new AbortController();

  fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(req),
    signal: controller.signal,
  }).then(async (response) => {
    const reader = response.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      let currentEvent = "";
      for (const line of lines) {
        if (line.startsWith("event:")) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith("data:") && currentEvent) {
          const data = JSON.parse(line.slice(5).trim());
          switch (currentEvent) {
            case "text":
              callbacks.onText(data.text);
              break;
            case "status":
              callbacks.onStatus(data.message, data.result);
              break;
            case "files":
              callbacks.onFiles(data);
              break;
            case "flow_steps":
              callbacks.onFlowSteps(data.steps);
              break;
            case "done":
              callbacks.onDone(data.elapsed_seconds, data.display_text, data.segments);
              break;
            case "error":
              callbacks.onError(data.message);
              break;
          }
          currentEvent = "";
        }
      }
    }
  }).catch((err) => {
    if (err.name !== "AbortError") {
      callbacks.onError(err.message);
    }
  });

  return controller;
}

export interface SupplementResult {
  thought_process: string;
  infographic_html: string;
  infographic_data: any;
  elapsed_seconds: number;
  error?: string;
}

export interface DeepDiveResult {
  questions: string[];
  error?: string;
}

export async function fetchSupplement(params: {
  user_prompt: string;
  display_text: string;
  company_display_name: string;
  company_folder_name: string;
  project_id?: string;
  gcs_bucket?: string;
}): Promise<SupplementResult> {
  const res = await fetch(`${API_BASE}/api/supplement`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return res.json();
}

export async function fetchDeepDive(params: {
  user_prompt: string;
  display_text: string;
  company_folder_name: string;
}): Promise<DeepDiveResult> {
  const res = await fetch(`${API_BASE}/api/deep-dive`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return res.json();
}

export interface HistoryEntry {
  id: string;
  text: string;
  ts: string;
}

export async function fetchHistory(company: string): Promise<HistoryEntry[]> {
  const res = await fetch(`${API_BASE}/api/history?company=${encodeURIComponent(company)}`);
  return res.json();
}

export async function addHistory(company: string, text: string): Promise<void> {
  await fetch(`${API_BASE}/api/history/add`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company, text }),
  });
}

export async function deleteHistory(company: string, entryId: string): Promise<void> {
  await fetch(`${API_BASE}/api/history/delete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company, entry_id: entryId }),
  });
}
