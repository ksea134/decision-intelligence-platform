/**
 * API client for DIP backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

/**
 * SSEストリーミングでチャットAPIを呼び出す。
 * コールバックでイベントを受信する。
 */
export function streamChat(
  req: ChatRequest,
  callbacks: {
    onText: (text: string) => void;
    onStatus: (message: string) => void;
    onFiles: (files: FilesData) => void;
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
              callbacks.onStatus(data.message);
              break;
            case "files":
              callbacks.onFiles(data);
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
