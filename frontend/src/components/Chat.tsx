"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Company, SmartCard, FilesData, streamChat } from "@/lib/api";
import SmartCards from "./SmartCards";
import Citations from "./Citations";
import MessageContent, { Segment } from "./MessageContent";
import Supplement from "./Supplement";
import RightColumn from "./RightColumn";
import QuestionHistory from "./QuestionHistory";
import { fetchSupplement, fetchHistory, addHistory, deleteHistory, HistoryEntry } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  files?: FilesData | null;
  segments?: Segment[] | null;
  userPrompt?: string;
  flowSteps?: any[];
}

interface ChatProps {
  company: Company;
}

export default function Chat({ company }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [loadingStartTime, setLoadingStartTime] = useState(0);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [streamingText, setStreamingText] = useState("");
  const [streamingFiles, setStreamingFiles] = useState<FilesData | null>(null);
  const [flowSteps, setFlowSteps] = useState<any[]>([]);
  const [thoughtProcess, setThoughtProcess] = useState("");
  const [supplementLoading, setSupplementLoading] = useState(false);
  const [questionHistory, setQuestionHistory] = useState<HistoryEntry[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // 企業が変わったらチャットをリセット + 履歴取得
  useEffect(() => {
    setMessages([]);
    setInput("");
    setStreamingText("");
    setStreamingFiles(null);
    setFlowSteps([]);
    setThoughtProcess("");
    fetchHistory(company.display_name).then(setQuestionHistory);
  }, [company.folder_name]);

  // 自動スクロール
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  // 経過秒数のリアルタイム更新（ローディング中のみ、通算秒数）
  useEffect(() => {
    if (!isLoading) return;
    const timer = setInterval(() => {
      setElapsedSec(Math.round((Date.now() - loadingStartTime) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [isLoading, loadingStartTime]);

  const handleNewChat = () => {
    setMessages([]);
    setInput("");
    setStreamingText("");
    setStreamingFiles(null);
    setFlowSteps([]);
    setThoughtProcess("");
  };

  const sendMessage = (question: string, source: "chat" | "smart_card", smartCardId?: string, dataSource?: string) => {
    if (isLoading) return;

    const userMsg: Message = { role: "user", content: question };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setSupplementLoading(false);
    setStatus("回答を生成しています…");
    setLoadingStartTime(Date.now());
    setElapsedSec(0);
    setStreamingText("");
    setStreamingFiles(null);
    setFlowSteps([]);

    let accumulatedText = "";
    let lastFlowSteps: any[] = [];

    abortRef.current = streamChat(
      {
        question,
        company_display_name: company.display_name,
        company_folder_name: company.folder_name,
        source,
        smart_card_id: smartCardId,
        data_source: dataSource || "all",
      },
      {
        onText: (text) => {
          accumulatedText += text;
          setStreamingText(accumulatedText);
        },
        onStatus: (message) => {
          setStatus(message);
        },
        onFiles: (files) => {
          setStreamingFiles(files);
        },
        onFlowSteps: (steps) => {
          lastFlowSteps = steps;
          setFlowSteps(steps);
        },
        onDone: (elapsed, displayText, segments) => {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: displayText || accumulatedText,
              files: streamingFiles,
              segments: segments || null,
              userPrompt: question,
              flowSteps: lastFlowSteps,
            },
          ]);
          setFlowSteps(lastFlowSteps);
          setStreamingText("");
          setStreamingFiles(null);
          setIsLoading(false);
          setStatus("");

          // 質問履歴に追加（スマートカード以外）
          if (source === "chat") {
            addHistory(company.display_name, question).then(() => {
              fetchHistory(company.display_name).then(setQuestionHistory);
            });
          }

          // 補足フェーズを自動実行（思考ロジック取得）
          setSupplementLoading(true);
          const finalText = displayText || accumulatedText;
          fetchSupplement({
            user_prompt: question,
            display_text: finalText,
            company_display_name: company.display_name,
            company_folder_name: company.folder_name,
          }).then((result) => {
            if (result.thought_process) {
              setThoughtProcess(result.thought_process);
            }
            setSupplementLoading(false);
          }).catch(() => {
            setSupplementLoading(false);
          });
        },
        onError: (message) => {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: `エラー: ${message}` },
          ]);
          setIsLoading(false);
          setStatus("");
        },
      },
    );
  };

  // flowStepsをstreamChatのコールバック外でキャプチャするため、
  // api.tsのonStatusで受け取ったflow_stepsを追跡する
  // → 現状はdoneイベントのsegmentsと同時に処理

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    const q = input.trim();
    setInput("");
    sendMessage(q, "chat");
  };

  const handleSmartCardClick = (card: SmartCard) => {
    sendMessage(`${card.icon} ${card.title}`, "smart_card", card.id, card.data_source);
  };

  const showSmartCards = messages.length === 0 && !isLoading;

  return (
    <div className="flex h-screen">
      {/* 左カラム: チャット（75%） */}
      <div className="flex-[3] flex flex-col min-w-0">
        {/* タイトル行 */}
        <div className="flex items-center justify-between pl-14 pr-6 py-3 border-b border-gray-800">
          <div>
            <span className="text-xs text-gray-400 tracking-wider">DIP | Decision Intelligence Platform</span>
            <h2 className="text-lg font-bold text-white">{company.display_name}</h2>
          </div>
          <button
            onClick={handleNewChat}
            className="text-sm text-gray-300 bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg transition-colors"
          >
            新規チャット
          </button>
        </div>

        {/* メッセージエリア */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          <SmartCards
            folderName={company.folder_name}
            onCardClick={handleSmartCardClick}
            visible={showSmartCards}
          />

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-3xl rounded-xl px-4 py-3 ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-800 text-gray-100"
                }`}
              >
                {msg.role === "assistant" ? (
                  <>
                    <MessageContent
                      segments={msg.segments || null}
                      fallbackText={msg.content}
                    />
                    <Citations files={msg.files || null} />
                    <Supplement
                      userPrompt={msg.userPrompt || ""}
                      displayText={msg.content}
                      companyDisplayName={company.display_name}
                      companyFolderName={company.folder_name}
                      onDeepDiveClick={(q) => sendMessage(q, "chat")}
                    />
                  </>
                ) : (
                  <p>{msg.content}</p>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="max-w-3xl rounded-xl px-4 py-3 bg-gray-800 text-gray-100">
                {streamingText ? (
                  <>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {streamingText}
                    </ReactMarkdown>
                    {streamingFiles && <Citations files={streamingFiles} />}
                  </>
                ) : (
                  <div className="flex items-center gap-2 text-gray-300">
                    <div className="w-3.5 h-3.5 rounded-full border-2 border-gray-500 border-t-green-500 animate-spin flex-shrink-0" />
                    <span className="text-sm">{status}（{elapsedSec}秒）</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 補足フェーズ処理中 */}
          {supplementLoading && (
            <div className="flex items-center gap-2 text-sm text-gray-400 px-2">
              <div className="w-3 h-3 rounded-full border-2 border-gray-500 border-t-green-500 animate-spin flex-shrink-0" />
              <span>補足情報を整理しています…</span>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* 入力欄 */}
        <div className="border-t border-gray-700 p-4">
          <QuestionHistory
            history={questionHistory}
            onRerun={(text) => sendMessage(text, "chat")}
            onDelete={(entryId) => {
              deleteHistory(company.display_name, entryId).then(() => {
                fetchHistory(company.display_name).then(setQuestionHistory);
              });
            }}
          />
          <span className="text-xs text-gray-400 tracking-wider">DI Conversation</span>
          <form onSubmit={handleSubmit} className="flex gap-2 mt-1">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={messages.length === 0 ? "本日はどのようなお手伝いをしましょうか。" : "追加でご質問はございますか。"}
              disabled={isLoading}
              className="flex-1 bg-gray-800 text-white rounded-lg px-4 py-3 text-sm
                         border border-gray-600 focus:border-blue-500 focus:outline-none
                         disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="bg-blue-600 text-white rounded-lg px-6 py-3 text-sm font-bold
                         hover:bg-blue-500 disabled:opacity-50 disabled:hover:bg-blue-600
                         transition-colors"
            >
              送信
            </button>
          </form>
        </div>
      </div>

      {/* 右カラム: 情報パネル（25%） */}
      <div className="flex-[1] border-l border-gray-700 bg-gray-900 min-w-0">
        <RightColumn
          folderName={company.folder_name}
          flowSteps={flowSteps}
          thoughtProcess={thoughtProcess}
        />
      </div>
    </div>
  );
}
