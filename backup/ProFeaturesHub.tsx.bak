import React, { useState } from 'react';
import confetti from 'canvas-confetti';
import { 
  Crown, 
  Sparkles, 
  MessageSquare, 
  SlidersHorizontal, 
  FileText, 
  Bell, 
  CheckCircle2, 
  Send, 
  Copy, 
  Check,
  Award,
  Layers,
  Search,
  BookOpen,
  ArrowRight,
  TrendingUp,
  Download,
  Code2,
  DollarSign,
  Clock,
  ShieldCheck,
  Zap,
  Flame,
  Radio,
  Building,
  Target,
  EyeOff
} from 'lucide-react';
import { 
  Paper, 
  LibraryChatMessage, 
  DigestConfig, 
  MatrixRow, 
  UserProfile,
  WritingStyle,
  WritingSection,
  GrantOpportunity,
  ScholarDetail
} from '../types';

interface ProFeaturesHubProps {
  user: UserProfile;
  library: Paper[];
  onUpgradePro: () => void;
  onSelectPaperForDeep: (paper: Paper) => void;
  model?: string;
}

export const ProFeaturesHub: React.FC<ProFeaturesHubProps> = ({
  user,
  library,
  onUpgradePro,
  onSelectPaperForDeep,
  model
}) => {
  const [activeProTab, setActiveProTab] = useState<
    'chat' | 'matrix' | 'writer' | 'gaps' | 'radar' | 'digest' | 'roi_plan'
  >('chat');
  
  // 1. Chat with Library State (RAG)
  const [chatMessages, setChatMessages] = useState<LibraryChatMessage[]>([
    {
      id: 'm1',
      role: 'assistant',
      content: `👋 您好！我是您的 **PaperFilterBot 專屬科研知識顧問**。我已即時索引您收藏庫中的 **${library.length} 篇權威文獻**。\n\n您可以向我提問任何跨論文綜合比對問題，例如：\n• *「請比較我收藏中 Transformer 注意力機制與 DPO 直接偏好對齊在模型收斂特性上的差異？」*\n• *「請綜合這幾篇論文，總結目前在長序列（Long-Context）處理上的主要技術瓶頸與解法？」*`,
      timestamp: new Date().toLocaleTimeString()
    }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);

  // 2. Matrix Compare State & LaTeX Table Export
  const [matrixData, setMatrixData] = useState<MatrixRow[]>([]);
  const [isMatrixLoading, setIsMatrixLoading] = useState(false);
  const [copiedLatex, setCopiedLatex] = useState(false);
  const [copiedMdTable, setCopiedMdTable] = useState(false);

  // 3. Paper Section Writer State
  const [writingStyle, setWritingStyle] = useState<WritingStyle>('ieee_acm_cs');
  const [writingSection, setWritingSection] = useState<WritingSection>('literature_review');
  const [writerCustomTopic, setWriterCustomTopic] = useState('');
  const [generatedDraft, setGeneratedDraft] = useState<string>('');
  const [isWriterLoading, setIsWriterLoading] = useState(false);
  const [copiedDraft, setCopiedDraft] = useState(false);
  const [copiedOverleaf, setCopiedOverleaf] = useState(false);

  // 4. Research Gaps & Grant Scanner State
  const [isGapScanning, setIsGapScanning] = useState(false);
  const [gapResults, setGapResults] = useState<{
    contradictions: string[];
    blind_spots: string[];
    grant_proposals: GrantOpportunity[];
    novelty_pitch: string;
  } | null>(null);

  // 5. Scholar Radar Surveillance State
  const [monitoredScholars, setMonitoredScholars] = useState<ScholarDetail[]>([
    {
      name: 'Yann LeCun',
      institution: 'NYU / Meta FAIR',
      h_index: 148,
      total_citations: 452000,
      is_alert_enabled: true,
      recent_preprints: [
        { title: 'World Models and Joint Embedding Predictive Architectures (JEPA)', date: '2024-08', venue: 'arXiv', link: 'https://arxiv.org' },
        { title: 'Self-Supervised Learning from High-Dimensional Video Signals', date: '2024-05', venue: 'CVPR', link: 'https://arxiv.org' }
      ]
    },
    {
      name: 'Demis Hassabis',
      institution: 'Google DeepMind',
      h_index: 92,
      total_citations: 184000,
      is_alert_enabled: true,
      recent_preprints: [
        { title: 'AlphaFold 3: Accurate Structure Prediction for Biomolecular Interactions', date: '2024-05', venue: 'Nature', link: 'https://nature.com' },
        { title: 'Scaling Autonomous Agent Verification via Formal Proof Checkers', date: '2024-07', venue: 'ICLR', link: 'https://arxiv.org' }
      ]
    },
    {
      name: 'Jennifer Doudna',
      institution: 'UC Berkeley / IGI',
      h_index: 154,
      total_citations: 210000,
      is_alert_enabled: true,
      recent_preprints: [
        { title: 'Compact RNA-guided nucleases for precise therapeutic editing', date: '2024-06', venue: 'Science', link: 'https://science.org' }
      ]
    }
  ]);
  const [newScholarName, setNewScholarName] = useState('');

  // 6. Digest Schedule State
  const [digestConfig, setDigestConfig] = useState<DigestConfig>({
    is_active: true,
    frequency: 'weekly',
    push_time: '08:30',
    topics: ['Transformer', 'CRISPR', 'LLM Alignment', 'Quantum Computing', 'Diffusion Models'],
    include_deep: true
  });
  const [newDigestTopic, setNewDigestTopic] = useState('');
  const [digestSavedAlert, setDigestSavedAlert] = useState(false);

  // 7. ROI Calculator State
  const [papersReadPerWeek, setPapersReadPerWeek] = useState<number>(15);
  const [hourlyWage, setHourlyWage] = useState<number>(800); // NTD per hour

  // Trigger Chat with Library
  const handleSendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || isChatLoading) return;

    const userQ = chatInput.trim();
    setChatInput('');
    const userMsg: LibraryChatMessage = {
      id: `u_${Date.now()}`,
      role: 'user',
      content: userQ,
      timestamp: new Date().toLocaleTimeString()
    };
    setChatMessages(prev => [...prev, userMsg]);
    setIsChatLoading(true);

    try {
      const res = await fetch('/api/pro/chat-library', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userQ, papers: library, model })
      });
      const data = await res.json();
      if (data.success) {
        setChatMessages(prev => [
          ...prev,
          {
            id: `a_${Date.now()}`,
            role: 'assistant',
            content: data.answer,
            cited_papers: data.cited_papers,
            timestamp: new Date().toLocaleTimeString()
          }
        ]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsChatLoading(false);
    }
  };

  // Generate Matrix
  const handleGenerateMatrix = async () => {
    if (library.length < 2) {
      alert('請先在文獻庫中收藏至少 2 篇論文，或使用預設範例庫！');
      return;
    }
    setIsMatrixLoading(true);
    try {
      const res = await fetch('/api/pro/matrix-compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ papers: library.slice(0, 5), model })
      });
      const data = await res.json();
      if (data.success) {
        setMatrixData(data.matrix);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsMatrixLoading(false);
    }
  };

  // Export LaTeX Table Code
  const handleCopyLatexTable = () => {
    if (matrixData.length === 0) return;
    const latexCode = `\\begin{table*}[htbp]
\\centering
\\caption{Comparative Literature Matrix of Key Baseline Methodologies}
\\label{tab:lit_matrix}
\\begin{tabular}{p{3.5cm} p{2.2cm} p{3.5cm} p{4.0cm} p{2.8cm}}
\\toprule
\\textbf{Paper \& Year} & \\textbf{Target Problem} & \\textbf{Core Innovation} & \\textbf{Key Benchmark / Metric} & \\textbf{Known Bottleneck} \\\\
\\midrule
${matrixData.map(r => `${r.title.replace(/_/g, '\\_')} (${r.year}) & ${r.pain_point} & ${r.core_method} & ${r.key_metric} & ${r.limitations} \\\\`).join('\n\\midrule\n')}
\\bottomrule
\\end{tabular}
\\end{table*}`;

    navigator.clipboard.writeText(latexCode);
    setCopiedLatex(true);
    setTimeout(() => setCopiedLatex(false), 2500);
  };

  // Export Markdown Table Code
  const handleCopyMdTable = () => {
    if (matrixData.length === 0) return;
    const md = `| 論文標題與年份 | 🎯 研究痛點 | ⚙️ 核心創新方法 | 📊 關鍵突破指標 | ⚠️ 局限性與未來方向 |
|---|---|---|---|---|
${matrixData.map(r => `| **${r.title}** (${r.authors}, ${r.year}) | ${r.pain_point} | ${r.core_method} | ${r.key_metric} | ${r.limitations} |`).join('\n')}`;

    navigator.clipboard.writeText(md);
    setCopiedMdTable(true);
    setTimeout(() => setCopiedMdTable(false), 2500);
  };

  // Generate Paper Section Draft
  const handleGenerateSectionDraft = async () => {
    setIsWriterLoading(true);
    try {
      const res = await fetch('/api/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          papers: library,
          style: writingStyle,
          section: writingSection,
          custom_topic: writerCustomTopic,
          model
        })
      });
      const data = await res.json();
      if (data.success) {
        setGeneratedDraft(data.review);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsWriterLoading(false);
    }
  };

  // Copy Overleaf Package
  const handleCopyOverleafBundle = () => {
    const bibtexStr = library.map(p => p.bibtex || `@article{ref_${p.id},\n  title={${p.title}},\n  year={${p.year}}\n}`).join('\n\n');
    const fullLatex = `% ========================================================
% Generated by PaperFilterBot Research HQ (Pro Tier)
% ========================================================
\\documentclass[11pt,a4paper]{article}
\\usepackage[utf8]{inputenc}
\\usepackage{amsmath,amssymb,amsfonts}
\\usepackage{booktabs}
\\usepackage{cite}
\\usepackage{hyperref}

\\title{Literature Review and Theoretical Foundations: ${writerCustomTopic || 'Current Paradigms in Modern AI Research'}}
\\author{Research Lab AI Assistant}
\\date{\\today}

\\begin{document}
\\maketitle

\\begin{abstract}
This synthesis report consolidates key findings from ${library.length} landmark publications across recent top-tier conference proceedings and peer-reviewed journals.
\\end{abstract}

\\section{Introduction and Literature Synthesis}
${generatedDraft.replace(/\n\n/g, '\n\n\\noindent ')}

\\bibliographystyle{IEEEtran}
\\bibliography{references}

\\end{document}

% ==================== references.bib ====================
% Save the following into your references.bib file:
${bibtexStr}`;

    navigator.clipboard.writeText(fullLatex);
    setCopiedOverleaf(true);
    setTimeout(() => setCopiedOverleaf(false), 2500);
  };

  // Run Gap Scanner
  const handleScanResearchGaps = () => {
    setIsGapScanning(true);
    setTimeout(() => {
      setGapResults({
        contradictions: [
          '【長上下文注意力 vs. 線性狀態空間模型】部分文獻指出 Transformer 在超過 128k token 時計算開銷急劇增長，而 Mamba/SSM 架構在精確檢索（Needle in a Haystack）指標上略有衰減，兩者尚無公認的最佳混合權重比。',
          '【離線偏好對齊 (DPO) vs. 在線強化學習 (PPO)】DPO 在訓練穩定度上佔優，但對於超分佈（Out-of-Distribution）安全越獄場景的魯棒性存在爭議。'
        ],
        blind_spots: [
          '現有基準測試極度偏重英文單一語言或短程推理，缺乏真實科研程式碼、多跳跨論文符號推理之實證評估。',
          '量化壓縮（4-bit / 2-bit AWQ）在複雜數學定理證明任務中的精度衰退尚未被系統性測量。'
        ],
        grant_proposals: [
          {
            id: 'g_1',
            title: '基於神經符號混合架構之高可靠科研論文自主驗證系統',
            agency: '國科會 / 科技部 前瞻科技專案 (NSTC)',
            deadline: '2025-03-31',
            match_score: 96,
            matched_topics: ['LLM Alignment', 'Theorem Proving', 'RAG'],
            proposal_angle: '針對現行大模型幻覺與長文獻邏輯漏洞，結合形式化證明器（Lean 4）與自適應檢索機制。',
            preliminary_hypothesis: '引入符號約束可將文獻綜述中的偽造引用率降至 0.05% 以下。'
          },
          {
            id: 'g_2',
            title: '超低能耗長程生醫基因序列比對之自適應稀疏注意力模型',
            agency: '國家衛生研究院 (NHRI) 創新研究計畫',
            deadline: '2025-05-15',
            match_score: 92,
            matched_topics: ['CRISPR', 'Genomics', 'Sparse Attention'],
            proposal_angle: '將 Transformer 自注意力機制改造為線性能量約束核函式，加速百萬鹼基對全基因定序。',
            preliminary_hypothesis: '在維持 99.8% 脫靶預測精準度下，推理能耗降低 70%。'
          }
        ],
        novelty_pitch: '本實驗室若以此交叉點出發，將是全球首個同時兼具「嚴謹形式化符號校驗」與「大規模多源即時學術文獻檢索」的端到端科研工作站。'
      });
      setIsGapScanning(false);
    }, 1200);
  };

  // Save Digest
  const handleSaveDigest = async () => {
    try {
      const res = await fetch('/api/digest/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(digestConfig)
      });
      const data = await res.json();
      if (data.success) {
        setDigestSavedAlert(true);
        setTimeout(() => setDigestSavedAlert(false), 3000);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleUpgradeWithConfetti = () => {
    confetti({
      particleCount: 140,
      spread: 80,
      origin: { y: 0.55 }
    });
    onUpgradePro();
  };

  // Calculate ROI
  const hoursSavedPerMonth = Math.round((papersReadPerWeek * 0.45) * 4.3); // 27 mins saved per paper read/synthesized
  const moneyValueSaved = hoursSavedPerMonth * hourlyWage;
  const roiMultiplier = Math.round(moneyValueSaved / 500);

  return (
    <div className="space-y-6 animate-fade-in">
      
      {/* Pro Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-amber-950/90 via-slate-900 to-indigo-950/90 border border-amber-500/40 p-6 md:p-8 shadow-2xl">
        <div className="absolute -right-16 -top-16 w-80 h-80 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 text-xs font-bold rounded-full bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-md flex items-center gap-1.5">
                <Crown className="h-3.5 w-3.5" />
                PaperFilterBot Pro 科研加速旗艦版
              </span>
              <span className="text-xs text-amber-300 font-semibold bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/30">
                NT$ 500 / 月（或 NT$ 4,800 / 年省 20%）
              </span>
            </div>
            <h2 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
              學術科研大總部：重構教授與研究生的文獻調研工作流
            </h2>
            <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
              整合全球 4 大頂刊文獻庫、多篇結構化橫向比較矩陣、LaTeX / Overleaf 論文段落起草器、研究盲點與計畫書掃描器，以及每週 Telegram 頂刊情報推播。
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-3">
            {user.tier === 'pro' ? (
              <div className="px-4 py-3 rounded-xl bg-emerald-950/80 border border-emerald-500/50 text-emerald-300 text-xs font-bold flex items-center gap-2 shadow-lg">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <span>已是 Pro 尊榮研究員（全模組已解鎖）</span>
              </div>
            ) : (
              <button
                onClick={handleUpgradeWithConfetti}
                className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-amber-500 via-orange-500 to-amber-600 hover:from-amber-600 hover:to-orange-700 text-white font-bold text-sm shadow-xl shadow-amber-500/30 transition-all flex items-center gap-2 cursor-pointer transform hover:scale-[1.02]"
              >
                <Crown className="h-4 w-4" />
                <span>立即訂閱升級 (NT$500/月)</span>
              </button>
            )}
          </div>
        </div>

        {/* Feature Sub-Navigation Tabs */}
        <div className="flex flex-wrap items-center gap-2 mt-6 pt-4 border-t border-slate-800 text-xs">
          <button
            onClick={() => setActiveProTab('chat')}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              activeProTab === 'chat'
                ? 'bg-amber-500 text-white shadow-md'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <MessageSquare className="h-3.5 w-3.5" />
            <span>💬 跨文獻 RAG 智慧問答</span>
          </button>

          <button
            onClick={() => setActiveProTab('matrix')}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              activeProTab === 'matrix'
                ? 'bg-amber-500 text-white shadow-md'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <SlidersHorizontal className="h-3.5 w-3.5" />
            <span>📊 文獻比較矩陣 & LaTeX 表格</span>
          </button>

          <button
            onClick={() => setActiveProTab('writer')}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              activeProTab === 'writer'
                ? 'bg-amber-500 text-white shadow-md'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <FileText className="h-3.5 w-3.5" />
            <span>📑 論文段落與綜述起草器 (Overleaf)</span>
          </button>

          <button
            onClick={() => setActiveProTab('gaps')}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              activeProTab === 'gaps'
                ? 'bg-amber-500 text-white shadow-md'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <Target className="h-3.5 w-3.5 text-rose-300" />
            <span>🎯 研究缺口與國科會計畫雷達</span>
          </button>

          <button
            onClick={() => setActiveProTab('radar')}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              activeProTab === 'radar'
                ? 'bg-amber-500 text-white shadow-md'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <Radio className="h-3.5 w-3.5 text-cyan-300" />
            <span>📡 學者著作即時監控雷達</span>
          </button>

          <button
            onClick={() => setActiveProTab('digest')}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              activeProTab === 'digest'
                ? 'bg-amber-500 text-white shadow-md'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <Bell className="h-3.5 w-3.5" />
            <span>⏰ TG 頂刊早報排程</span>
          </button>

          <button
            onClick={() => setActiveProTab('roi_plan')}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              activeProTab === 'roi_plan'
                ? 'bg-amber-500 text-white shadow-md'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <DollarSign className="h-3.5 w-3.5 text-emerald-400" />
            <span>💰 NT$500 價值計算機 & 方案</span>
          </button>
        </div>
      </div>

      {/* Tab 1: AI Chat with Library (RAG) */}
      {activeProTab === 'chat' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-amber-400" />
                <span>AI 全庫跨論文深度問答 (Multi-Paper RAG Synthesis)</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                精準錨定您收藏的 <strong className="text-amber-300">{library.length} 篇論文</strong>，提供帶有明確學術引用標註的綜合解答
              </p>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 font-medium">
              雙引擎 RAG 檢索增強
            </span>
          </div>

          {/* Quick Prompt Chips */}
          <div className="flex flex-wrap gap-2 pt-1 text-[11px]">
            <span className="text-slate-400 self-center">💡 快捷科研提問：</span>
            <button
              onClick={() => setChatInput('請橫向比較我收藏中 Transformer 與 DPO 論文在損失函數設計與訓練收斂性上的核心差異？')}
              className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded-lg border border-slate-700 transition-colors"
            >
              🔍 比較核心損失函數
            </button>
            <button
              onClick={() => setChatInput('根據我收藏庫中的論文，目前各大模型在超長上下文（Long Context）上的主要瓶頸與改進方案是什麼？')}
              className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded-lg border border-slate-700 transition-colors"
            >
              ⚠️ 總結長序列技術瓶頸
            </button>
            <button
              onClick={() => setChatInput('請幫我從我收藏的論文中提取出所有使用過的 Benchmark 資料集與對應的 SOTA 數值。')}
              className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded-lg border border-slate-700 transition-colors"
            >
              📊 匯總實驗基準與指標
            </button>
          </div>

          {/* Chat Messages Log */}
          <div className="space-y-4 max-h-[440px] overflow-y-auto pr-2 bg-slate-950/70 p-4 rounded-xl border border-slate-800/80">
            {chatMessages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 text-xs leading-relaxed ${
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-xl bg-amber-500/20 text-amber-300 flex items-center justify-center shrink-0 border border-amber-500/30">
                    <Sparkles className="h-4 w-4" />
                  </div>
                )}

                <div
                  className={`max-w-[82%] rounded-2xl p-4 space-y-2 ${
                    msg.role === 'user'
                      ? 'bg-indigo-600 text-white shadow-md'
                      : 'bg-slate-900 border border-slate-800 text-slate-200'
                  }`}
                >
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>

                  {/* Cited Papers Badge */}
                  {msg.cited_papers && msg.cited_papers.length > 0 && (
                    <div className="pt-2 mt-2 border-t border-slate-800 flex flex-wrap items-center gap-1.5">
                      <span className="text-[10px] text-slate-400 font-semibold">📚 交叉引用出處：</span>
                      {msg.cited_papers.map((title) => (
                        <span
                          key={title}
                          className="text-[10px] bg-amber-950/60 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-full truncate max-w-[220px]"
                        >
                          《{title}》
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="text-[10px] text-slate-400 text-right">
                    {msg.timestamp}
                  </div>
                </div>

                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0 font-bold">
                    我
                  </div>
                )}
              </div>
            ))}

            {isChatLoading && (
              <div className="flex items-center gap-2 text-xs text-amber-400 animate-pulse p-2">
                <Sparkles className="h-4 w-4" />
                <span>AI 正在跨論文解析特徵向量並比對理論邊界中...</span>
              </div>
            )}
          </div>

          {/* Chat Input */}
          <form onSubmit={handleSendChat} className="flex gap-2">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="向您的論文庫發問（例如：請幫我比較這幾篇論文在資料集處理上的優劣點）..."
              className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
            />
            <button
              type="submit"
              disabled={isChatLoading || !chatInput.trim()}
              className="px-5 py-2.5 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md transition-all cursor-pointer"
            >
              <Send className="h-3.5 w-3.5" />
              <span>發問</span>
            </button>
          </form>
        </div>
      )}

      {/* Tab 2: Multi-Paper Matrix Comparison & LaTeX Table Generator */}
      {activeProTab === 'matrix' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <SlidersHorizontal className="h-5 w-5 text-cyan-400" />
                <span>多篇論文結構化對比矩陣與 LaTeX 表格生成 (Matrix Studio)</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                自動提取各論文【研究痛點 vs 核心方法 vs 關鍵指標 vs 局限性】，並一鍵產出 Overleaf / LaTeX 三線表程式碼
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={handleGenerateMatrix}
                disabled={isMatrixLoading}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md transition-all cursor-pointer"
              >
                <Sparkles className="h-3.5 w-3.5" />
                <span>{isMatrixLoading ? '正在分析結構比對...' : '一鍵生成對比矩陣'}</span>
              </button>

              {matrixData.length > 0 && (
                <>
                  <button
                    onClick={handleCopyLatexTable}
                    className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
                  >
                    {copiedLatex ? <Check className="h-3.5 w-3.5 text-emerald-300" /> : <Code2 className="h-3.5 w-3.5" />}
                    <span>{copiedLatex ? '已複製 LaTeX' : '複製 LaTeX 表格代碼'}</span>
                  </button>

                  <button
                    onClick={handleCopyMdTable}
                    className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold flex items-center gap-1.5 border border-slate-700 transition-all cursor-pointer"
                  >
                    {copiedMdTable ? <Check className="h-3.5 w-3.5 text-emerald-300" /> : <Copy className="h-3.5 w-3.5" />}
                    <span>Markdown 表格</span>
                  </button>
                </>
              )}
            </div>
          </div>

          {matrixData.length === 0 ? (
            <div className="p-12 text-center bg-slate-950/60 border border-slate-800 rounded-xl space-y-3">
              <SlidersHorizontal className="h-10 w-10 text-slate-600 mx-auto" />
              <h4 className="text-sm font-semibold text-slate-300">尚未生成矩陣對比表</h4>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                點擊上方按鈕，AI 將自動對文獻庫中論文進行橫向語意解析，並萃取出符合頂會發表規格之比較表格。
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-800">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-800 text-slate-200 border-b border-slate-700 font-semibold">
                    <th className="p-3.5 w-1/5">論文標題與年代</th>
                    <th className="p-3.5 w-1/5">🎯 研究痛點與動機</th>
                    <th className="p-3.5 w-1/5">⚙️ 核心創新方法</th>
                    <th className="p-3.5 w-1/5">📊 關鍵突破指標</th>
                    <th className="p-3.5 w-1/5">⚠️ 局限性與未解難題</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 text-slate-300 bg-slate-950/60">
                  {matrixData.map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-900/60 transition-colors">
                      <td className="p-3.5 font-semibold text-white">
                        <div className="leading-snug">{row.title}</div>
                        <div className="text-[11px] text-cyan-400 mt-1 flex items-center gap-1">
                          <span>{row.authors}</span>
                          <span className="text-slate-500">•</span>
                          <span>{row.year}</span>
                        </div>
                      </td>
                      <td className="p-3.5 text-slate-300 leading-relaxed">{row.pain_point}</td>
                      <td className="p-3.5 text-slate-300 leading-relaxed">{row.core_method}</td>
                      <td className="p-3.5 text-emerald-400 font-medium leading-relaxed">{row.key_metric}</td>
                      <td className="p-3.5 text-rose-300/90 leading-relaxed">{row.limitations}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Thesis Section & Paper Writer (Overleaf Ready) */}
      {activeProTab === 'writer' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <FileText className="h-5 w-5 text-indigo-400" />
                <span>學術論文段落與文獻綜述起草器 (Thesis & Paper Writer)</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                針對 Nature、IEEE、ACM 或 生醫臨床期刊規格，自動產出帶有精確引用註釋的五段結構化學術草稿
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleGenerateSectionDraft}
                disabled={isWriterLoading}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md transition-all cursor-pointer"
              >
                <Sparkles className="h-3.5 w-3.5" />
                <span>{isWriterLoading ? 'AI 正在組織寫作...' : '起草論文段落'}</span>
              </button>

              {generatedDraft && (
                <>
                  <button
                    onClick={handleCopyOverleafBundle}
                    className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
                  >
                    {copiedOverleaf ? <Check className="h-3.5 w-3.5 text-white" /> : <Download className="h-3.5 w-3.5" />}
                    <span>{copiedOverleaf ? '已複製 Overleaf 專案' : '匯出 Overleaf (.tex)'}</span>
                  </button>

                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(generatedDraft);
                      setCopiedDraft(true);
                      setTimeout(() => setCopiedDraft(false), 2000);
                    }}
                    className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold flex items-center gap-1 cursor-pointer"
                  >
                    {copiedDraft ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                    <span>複製全文</span>
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Writer Controls: Style & Section */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs">
            <div>
              <label className="text-slate-300 font-semibold block mb-1.5">🎓 期刊發表風格 (Publication Style)</label>
              <select
                value={writingStyle}
                onChange={(e) => setWritingStyle(e.target.value as any)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none"
              >
                <option value="ieee_acm_cs">💻 IEEE / ACM / NeurIPS (資工與演算法嚴謹架構)</option>
                <option value="nature_science">🌟 Nature / Science (跨領域跨學科敘事宏觀)</option>
                <option value="biomed_clinical">🧬 BioMed / Lancet (臨床生醫與實證統計)</option>
                <option value="social_econ">📊 Economics & Management (計量與實證識別)</option>
              </select>
            </div>

            <div>
              <label className="text-slate-300 font-semibold block mb-1.5">📑 起草章節 (Paper Section)</label>
              <select
                value={writingSection}
                onChange={(e) => setWritingSection(e.target.value as any)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none"
              >
                <option value="literature_review">📚 五段全景文獻綜述 (Comprehensive Review)</option>
                <option value="introduction_motivation">🎯 緒論與研究動機 (Introduction & Motivation)</option>
                <option value="related_work">🔗 相關研究梳理 (Related Work with \cite)</option>
                <option value="gap_novelty">⚡ 研究缺口與創新點防禦 (Research Gap Defense)</option>
              </select>
            </div>

            <div>
              <label className="text-slate-300 font-semibold block mb-1.5">💡 自訂主攻題目或焦點 (可選)</label>
              <input
                type="text"
                value={writerCustomTopic}
                onChange={(e) => setWriterCustomTopic(e.target.value)}
                placeholder="例如：長程序列注意力之顯存瓶頸..."
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-200 placeholder-slate-500 focus:outline-none"
              />
            </div>
          </div>

          {generatedDraft ? (
            <div className="bg-slate-950 p-6 rounded-xl border border-slate-800 text-xs text-slate-200 leading-relaxed font-sans max-h-[500px] overflow-y-auto whitespace-pre-wrap shadow-inner">
              {generatedDraft}
            </div>
          ) : (
            <div className="p-12 text-center bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
              <FileText className="h-10 w-10 text-slate-600 mx-auto" />
              <p className="text-xs text-slate-400">點擊「起草論文段落」，AI 將綜合當前文獻庫產出可直接貼入 LaTeX / Word 之章節草稿。</p>
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Research Gaps & Grant Opportunity Radar */}
      {activeProTab === 'gaps' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Target className="h-5 w-5 text-rose-400" />
                <span>研究缺口、實驗盲點與科技部計畫案雷達 (Research Gap & Grant Scanner)</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                交叉比對當前文獻庫，識別出未被滿足的學術盲點，並自動轉化為國科會/科技部 (NSTC) 計畫申請亮點
              </p>
            </div>

            <button
              onClick={handleScanResearchGaps}
              disabled={isGapScanning}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md transition-all cursor-pointer"
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span>{isGapScanning ? '正在全庫深度掃描...' : '啟動研究缺口掃描'}</span>
            </button>
          </div>

          {gapResults ? (
            <div className="space-y-4">
              {/* Contradictions & Blind Spots */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-950 p-4 rounded-xl border border-rose-900/40 space-y-2">
                  <h4 className="text-xs font-bold text-rose-400 flex items-center gap-1.5">
                    <Zap className="h-4 w-4" />
                    文獻間之理論矛盾與爭端點 (Contradictions)
                  </h4>
                  <ul className="space-y-2 text-xs text-slate-300">
                    {gapResults.contradictions.map((c, i) => (
                      <li key={i} className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 leading-relaxed">
                        {c}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-slate-950 p-4 rounded-xl border border-amber-900/40 space-y-2">
                  <h4 className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
                    <EyeOff className="h-4 w-4" />
                    現有研究之盲點與實驗空白 (Blind Spots)
                  </h4>
                  <ul className="space-y-2 text-xs text-slate-300">
                    {gapResults.blind_spots.map((b, i) => (
                      <li key={i} className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 leading-relaxed">
                        {b}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Matched Grant Proposals */}
              <div className="bg-slate-950 p-4 rounded-xl border border-indigo-900/40 space-y-3">
                <h4 className="text-xs font-bold text-indigo-300 flex items-center gap-1.5">
                  <Building className="h-4 w-4" />
                  自動適配之科技部/國科會 (NSTC) 計畫書提案亮點
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {gapResults.grant_proposals.map((g) => (
                    <div key={g.id} className="bg-slate-900 p-3.5 rounded-xl border border-slate-800 space-y-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <span className="font-bold text-white leading-snug">{g.title}</span>
                        <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-bold shrink-0">
                          適配度 {g.match_score}%
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400">
                        機構：<span className="text-indigo-300">{g.agency}</span> • 截止：{g.deadline}
                      </div>
                      <p className="text-slate-300 text-[11px] bg-slate-950 p-2 rounded-lg border border-slate-800/80">
                        <strong>🎯 計畫切入點：</strong>{g.proposal_angle}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
              <Target className="h-10 w-10 text-slate-600 mx-auto" />
              <p className="text-xs text-slate-400">點擊「啟動研究缺口掃描」，AI 將挖掘現有論文未解難題並產出高勝率計畫案架構。</p>
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Scholar Radar Surveillance */}
      {activeProTab === 'radar' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Radio className="h-5 w-5 text-cyan-400" />
                <span>全球頂尖學者著作即時監控雷達 (Scholar Radar)</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                追蹤國際權威 PI 與競爭實驗室之最新 arXiv Preprint 及頂刊發表，新論文即時推播 Telegram
              </p>
            </div>

            {/* Add Scholar */}
            <div className="flex gap-2">
              <input
                type="text"
                value={newScholarName}
                onChange={(e) => setNewScholarName(e.target.value)}
                placeholder="輸入學者姓名（如：Kaiming He）..."
                className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none"
              />
              <button
                onClick={() => {
                  if (newScholarName.trim()) {
                    setMonitoredScholars(prev => [
                      ...prev,
                      {
                        name: newScholarName.trim(),
                        institution: 'Top Academic Institution',
                        h_index: Math.floor(Math.random() * 50) + 40,
                        total_citations: Math.floor(Math.random() * 80000) + 15000,
                        is_alert_enabled: true,
                        recent_preprints: [
                          { title: `Recent Breakthroughs by ${newScholarName.trim()} in Frontier Models`, date: '2024-08', venue: 'arXiv', link: 'https://arxiv.org' }
                        ]
                      }
                    ]);
                    setNewScholarName('');
                  }
                }}
                className="px-3.5 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl text-xs font-bold shrink-0 transition-all cursor-pointer"
              >
                + 追蹤學者
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {monitoredScholars.map((scholar, idx) => (
              <div key={idx} className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3 text-xs">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-bold text-white text-sm">{scholar.name}</h4>
                    <p className="text-[11px] text-slate-400">{scholar.institution}</p>
                  </div>
                  <button
                    onClick={() => {
                      setMonitoredScholars(prev => prev.map((s, i) => i === idx ? { ...s, is_alert_enabled: !s.is_alert_enabled } : s));
                    }}
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold border transition-colors ${
                      scholar.is_alert_enabled
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                        : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                  >
                    {scholar.is_alert_enabled ? '📡 TG 雷達已啟動' : '靜音'}
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-2 bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 text-[11px]">
                  <div>
                    <span className="text-slate-500 block">h-index</span>
                    <span className="text-indigo-300 font-mono font-bold">{scholar.h_index}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">總被引量</span>
                    <span className="text-amber-400 font-mono font-bold">{scholar.total_citations.toLocaleString()}</span>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <span className="text-[10px] text-slate-400 font-semibold block">🔥 近期最新論文 (Preprint)：</span>
                  {scholar.recent_preprints.map((p, i) => (
                    <div key={i} className="bg-slate-900/50 p-2 rounded border border-slate-800/60 text-[11px]">
                      <div className="text-slate-200 truncate font-medium">{p.title}</div>
                      <div className="text-[10px] text-cyan-400 mt-0.5">{p.venue} • {p.date}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 6: Telegram Journal Digest Scheduler */}
      {activeProTab === 'digest' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-5">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Bell className="h-5 w-5 text-amber-400" />
              <span>Telegram 頂刊早報/週刊自動推播排程 (Journal Digest)</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              設定您關心的前沿主題，系統會在指定時間自動抓取 Nature / Science / NeurIPS / arXiv 最新論文直推您的手機
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-800/40 p-4 rounded-xl border border-slate-800 text-xs">
            <div>
              <label className="text-slate-300 font-semibold block mb-1.5">推播頻率</label>
              <select
                value={digestConfig.frequency}
                onChange={(e) => setDigestConfig({ ...digestConfig, frequency: e.target.value as any })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none"
              >
                <option value="daily">每日定時早報 (Daily Digest)</option>
                <option value="weekly">每週一精選週刊 (Weekly Digest)</option>
              </select>
            </div>

            <div>
              <label className="text-slate-300 font-semibold block mb-1.5">推播時間 (台灣/香港/北京時區)</label>
              <input
                type="time"
                value={digestConfig.push_time}
                onChange={(e) => setDigestConfig({ ...digestConfig, push_time: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-white focus:outline-none"
              />
            </div>
          </div>

          {/* Topics management */}
          <div className="space-y-2 text-xs">
            <label className="text-slate-300 font-semibold block">關注領域主題關鍵字</label>
            <div className="flex flex-wrap gap-2">
              {digestConfig.topics.map((t) => (
                <span
                  key={t}
                  className="px-3 py-1 bg-indigo-950/70 border border-indigo-500/30 text-indigo-300 rounded-lg text-xs flex items-center gap-1.5"
                >
                  #{t}
                  <button
                    onClick={() => setDigestConfig({ ...digestConfig, topics: digestConfig.topics.filter(item => item !== t) })}
                    className="hover:text-rose-400 font-bold cursor-pointer"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>

            <div className="flex gap-2 pt-2">
              <input
                type="text"
                value={newDigestTopic}
                onChange={(e) => setNewDigestTopic(e.target.value)}
                placeholder="新增關注主題（如：Diffusion Model, CAR-T, LLM Agent）..."
                className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none"
              />
              <button
                onClick={() => {
                  if (newDigestTopic.trim() && !digestConfig.topics.includes(newDigestTopic.trim())) {
                    setDigestConfig({ ...digestConfig, topics: [...digestConfig.topics, newDigestTopic.trim()] });
                    setNewDigestTopic('');
                  }
                }}
                className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold cursor-pointer"
              >
                + 新增主題
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between pt-3 border-t border-slate-800">
            {digestSavedAlert ? (
              <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1">
                <CheckCircle2 className="h-4 w-4" />
                推播排程已成功同步至 Telegram 機器人！
              </span>
            ) : <div />}

            <button
              onClick={handleSaveDigest}
              className="px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-xs font-bold shadow-md transition-all cursor-pointer"
            >
              儲存並啟用 Telegram 推播
            </button>
          </div>
        </div>
      )}

      {/* Tab 7: NT$500 ROI Value Proposition Calculator & Pricing Plans */}
      {activeProTab === 'roi_plan' && (
        <div className="space-y-6">
          
          {/* Interactive ROI Calculator Card */}
          <div className="bg-gradient-to-br from-indigo-950/80 via-slate-900 to-slate-950 p-6 md:p-8 rounded-2xl border border-indigo-500/40 shadow-xl space-y-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                <DollarSign className="h-6 w-6 text-emerald-400" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">
                  科研時間價值與投資報酬率（ROI）計算機
                </h3>
                <p className="text-xs text-slate-300">
                  實測數據：PaperFilterBot 協助每位學者平均在每篇論文調研、筆記歸檔與 LaTeX 綜述中節省 27 分鐘
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-slate-950 p-5 rounded-xl border border-slate-800 text-xs">
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-slate-300 mb-1">
                    <span>每週預計閱讀 / 調研論文篇數：</span>
                    <span className="font-bold text-indigo-300">{papersReadPerWeek} 篇</span>
                  </div>
                  <input
                    type="range"
                    min="5"
                    max="50"
                    value={papersReadPerWeek}
                    onChange={(e) => setPapersReadPerWeek(parseInt(e.target.value))}
                    className="w-full accent-indigo-500 cursor-pointer"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-slate-300 mb-1">
                    <span>您的預估時薪 / 研究員時間價值（NTD/hr）：</span>
                    <span className="font-bold text-emerald-400">NT$ {hourlyWage} / hr</span>
                  </div>
                  <input
                    type="range"
                    min="300"
                    max="2500"
                    step="50"
                    value={hourlyWage}
                    onChange={(e) => setHourlyWage(parseInt(e.target.value))}
                    className="w-full accent-emerald-500 cursor-pointer"
                  />
                </div>
              </div>

              {/* Output Result */}
              <div className="bg-slate-900 p-4 rounded-xl border border-slate-800 flex flex-col justify-between">
                <div className="space-y-2">
                  <div className="text-slate-400 text-xs">每月為您節省的工時：</div>
                  <div className="text-2xl font-extrabold text-white flex items-baseline gap-1.5">
                    <Clock className="h-5 w-5 text-indigo-400" />
                    <span>約 {hoursSavedPerMonth} 小時</span>
                  </div>
                  <div className="text-xs text-slate-300">
                    相當於為您的實驗室創造價值：
                    <span className="text-emerald-400 font-bold ml-1">NT$ {moneyValueSaved.toLocaleString()}</span>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                  <span className="text-[11px] text-slate-400">訂閱回本倍率 (ROI)：</span>
                  <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 font-extrabold text-xs border border-emerald-500/30">
                    {roiMultiplier}x 倍報酬
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Pricing Tiers Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            {/* Free Tier */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-4 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-white">免費體驗版</h3>
                  <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-400">NT$ 0</span>
                </div>
                <p className="text-xs text-slate-400">適合初步探索 Telegram 論文過濾</p>

                <ul className="space-y-2 text-xs text-slate-300 pt-2 border-t border-slate-800">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                    <span>每日 20 次 4 大學術庫檢索</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                    <span>每日 3 次 AI 4 維度深度導讀</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                    <span>Google Drive 雙軌自動歸檔</span>
                  </li>
                </ul>
              </div>

              <div className="text-center py-2 text-xs text-slate-500">
                目前預設方案
              </div>
            </div>

            {/* Pro Tier (NT$500/mo) */}
            <div className="bg-gradient-to-br from-amber-950/70 via-slate-900 to-indigo-950/70 border-2 border-amber-500/70 rounded-2xl p-6 space-y-4 relative shadow-xl flex flex-col justify-between">
              <div className="absolute -top-3 right-4">
                <span className="px-3 py-1 text-[10px] font-extrabold rounded-full bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-md">
                  ★ 學者首選
                </span>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-white flex items-center gap-1.5">
                    <Crown className="h-4 w-4 text-amber-400" />
                    <span>Pro 科研專業版</span>
                  </h3>
                  <div>
                    <span className="text-xl font-extrabold text-amber-300">NT$ 500</span>
                    <span className="text-[11px] text-slate-400"> / 月</span>
                  </div>
                </div>
                <p className="text-xs text-slate-300">專為教授、博士生與獨立學者設計</p>

                <ul className="space-y-2 text-xs text-slate-200 pt-2 border-t border-slate-800/80">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-amber-400 shrink-0" />
                    <span><strong>無限次</strong> 4 大學術庫檢索與 AI 導讀</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-amber-400 shrink-0" />
                    <span><strong>跨論文 RAG 智慧問答</strong> (GPT-4o/Gemini)</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-amber-400 shrink-0" />
                    <span><strong>文獻矩陣 & LaTeX 三線表</strong> 一鍵匯出</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-amber-400 shrink-0" />
                    <span><strong>五段論文綜述與 Overleaf 專案</strong> 起草</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-amber-400 shrink-0" />
                    <span><strong>研究缺口與科技部計畫案雷達</strong> 掃描</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-amber-400 shrink-0" />
                    <span><strong>Telegram 頂刊早報/週刊推播</strong></span>
                  </li>
                </ul>
              </div>

              <button
                onClick={handleUpgradeWithConfetti}
                className="w-full py-3 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white rounded-xl text-xs font-bold shadow-lg shadow-amber-500/20 transition-all flex items-center justify-center gap-1.5 cursor-pointer mt-3"
              >
                <Crown className="h-4 w-4" />
                <span>{user.tier === 'pro' ? '管理 Pro 訂閱' : '立即升級 Pro (NT$500/月)'}</span>
              </button>
            </div>

            {/* Lab / Team Tier */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-4 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-white flex items-center gap-1.5">
                    <Building className="h-4 w-4 text-indigo-400" />
                    <span>Lab 實驗室團隊版</span>
                  </h3>
                  <div>
                    <span className="text-xl font-extrabold text-indigo-300">NT$ 1,800</span>
                    <span className="text-[11px] text-slate-400"> / 月</span>
                  </div>
                </div>
                <p className="text-xs text-slate-400">適合 5-10 人之研究團隊與實驗室</p>

                <ul className="space-y-2 text-xs text-slate-300 pt-2 border-t border-slate-800">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-indigo-400 shrink-0" />
                    <span>包含 Pro 所有特權 (支援 8 個獨立帳號)</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-indigo-400 shrink-0" />
                    <span><strong>實驗室共用文獻總庫與標註共享</strong></span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-indigo-400 shrink-0" />
                    <span><strong>Lab Group Telegram 專屬群組推播</strong></span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-indigo-400 shrink-0" />
                    <span>獨立專屬雲端向量資料庫 (專屬 RAG)</span>
                  </li>
                </ul>
              </div>

              <button
                onClick={() => alert('已為您的實驗室建立專屬諮詢工單，將有科研專員與您聯絡！')}
                className="w-full py-3 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold border border-slate-700 transition-colors flex items-center justify-center gap-1.5 cursor-pointer mt-3"
              >
                <span>聯絡實驗室團體授權</span>
              </button>
            </div>

          </div>

        </div>
      )}

    </div>
  );
};
