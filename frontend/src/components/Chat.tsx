"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Company, SmartCard, FilesData, streamChat } from "@/lib/api";
import SmartCards from "./SmartCards";
import Citations from "./Citations";

interface Message {
  role: "user" | "assistant";
  content: string;
  files?: FilesData | null;
}

interface ChatProps {
  company: Company;
}

export default function Chat({ company }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [streamingText, setStreamingText] = useState("");
  const [streamingFiles, setStreamingFiles] = useState<FilesData | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // 企業が変わったらチャットをリセット
  useEffect(() => {
    setMessages([]);
    setInput("");
    setStreamingText("");
    setStreamingFiles(null);
  }, [company.folder_name]);

  // 自動スクロール
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  const sendMessage = (question: string, source: "chat" | "smart_card", smartCardId?: string) => {
    if (isLoading) return;

    // ユーザーメッセージを追加
    const userMsg: Message = { role: "user", content: question };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setStatus("データを読み込んでいます...");
    setStreamingText("");
    setStreamingFiles(null);

    let accumulatedText = "";

    abortRef.current = streamChat(
      {
        question,
        company_display_name: company.display_name,
        company_folder_name: company.folder_name,
        source,
        smart_card_id: smartCardId,
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
        onDone: (elapsed, displayText) => {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: displayText || accumulatedText,
              files: streamingFiles,
            },
          ]);
          setStreamingText("");
          setStreamingFiles(null);
          setIsLoading(false);
          setStatus("");
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    const q = input.trim();
    setInput("");
    sendMessage(q, "chat");
  };

  const handleSmartCardClick = (card: SmartCard) => {
    sendMessage(`${card.icon} ${card.title}`, "smart_card", card.id);
  };

  const showSmartCards = messages.length === 0 && !isLoading;

  return (
    <div className="flex flex-col h-screen">
      {/* メッセージエリア */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {/* スマートカード */}
        <SmartCards
          folderName={company.folder_name}
          onCardClick={handleSmartCardClick}
          visible={showSmartCards}
        />

        {/* メッセージ履歴 */}
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
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                  <Citations files={msg.files || null} />
                </>
              ) : (
                <p>{msg.content}</p>
              )}
            </div>
          </div>
        ))}

        {/* ストリーミング中の表示 */}
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
                <div className="flex items-center gap-2 text-gray-400">
                  <div className="w-3 h-3 rounded-full border-2 border-gray-500 border-t-green-500 animate-spin" />
                  <span className="text-sm">{status}</span>
                </div>
              )}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* 入力欄 */}
      <div className="border-t border-gray-700 p-4">
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
  );
}
