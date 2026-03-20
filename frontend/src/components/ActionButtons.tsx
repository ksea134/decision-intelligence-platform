"use client";

interface ActionButtonsProps {
  question: string;
  answer: string;
  companyName: string;
}

function cleanMarkdown(text: string): string {
  return text
    .replace(/^#+\s+/gm, "")
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/\*(.*?)\*/g, "$1");
}

export default function ActionButtons({ question, answer, companyName }: ActionButtonsProps) {
  const plain = (question ? `【質問】\n${cleanMarkdown(question)}\n\n【回答】\n` : "") + cleanMarkdown(answer);
  const markdown = (question ? `## 質問\n\n${question}\n\n## 回答\n\n` : "") + answer;
  const now = new Date();
  const timestamp = `${now.getFullYear()}${String(now.getMonth()+1).padStart(2,"0")}${String(now.getDate()).padStart(2,"0")}-${String(now.getHours()).padStart(2,"0")}${String(now.getMinutes()).padStart(2,"0")}`;
  const safeCompany = companyName.replace(/[^\p{L}\p{N}\w\-]/gu, "_");

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(plain);
    } catch {
      const el = document.createElement("textarea");
      el.value = plain;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
    }
  };

  const handleTextDL = () => {
    const blob = new Blob([plain], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${timestamp}_${safeCompany}.txt`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const handlePDF = async () => {
    const { marked } = await import("marked");
    const htmlContent = await marked.parse(markdown);
    const printWindow = document.createElement("iframe");
    printWindow.style.cssText = "position:fixed;left:-9999px;width:0;height:0;";
    document.body.appendChild(printWindow);
    const doc = printWindow.contentDocument;
    if (!doc) return;
    doc.open();
    doc.write(`<!DOCTYPE html><html><head><meta charset="utf-8">
      <title>${timestamp}_Report_${safeCompany}</title>
      <style>
        body{font-family:'Helvetica Neue',Helvetica,'Hiragino Sans',Arial,sans-serif;
             color:#1a1a1a;line-height:1.8;padding:20px;}
        h1,h2,h3{margin-top:1em;margin-bottom:0.5em;}
        table{border-collapse:collapse;width:100%;}
        th,td{border:1px solid #ccc;padding:4px 8px;text-align:left;}
      </style></head><body>${htmlContent}</body></html>`);
    doc.close();
    setTimeout(() => {
      printWindow.contentWindow?.print();
      setTimeout(() => document.body.removeChild(printWindow), 1000);
    }, 300);
  };

  return (
    <div className="flex gap-2 mt-3">
      <button onClick={handleCopy}
        className="text-xs text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded transition-colors">
        コピー
      </button>
      <button onClick={handleTextDL}
        className="text-xs text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded transition-colors">
        テキスト
      </button>
      <button onClick={handlePDF}
        className="text-xs text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded transition-colors">
        PDF
      </button>
    </div>
  );
}
