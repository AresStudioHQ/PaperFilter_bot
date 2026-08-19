import React, { useState, useRef, useEffect } from 'react';
import { Send, User, RefreshCw, Link as LinkIcon, Globe, FolderPlus, ListOrdered, UserPlus, HelpCircle } from 'lucide-react';
import { BotMessage, Paper } from '../types';

interface BotSimulatorProps {
  userLang: string;
  onLanguageChange: (lang: string) => void;
  onOpenDeep: (paper: Paper) => void;
  onAddToLibrary: (paper: Paper) => void;
  onOpenSyncModal: () => void;
  onOpenProModal: () => void;
}

export const BotSimulator: React.FC<BotSimulatorProps> = ({ 
  userLang,
  onLanguageChange,
  onOpenDeep, 
  onAddToLibrary,
  onOpenSyncModal,
  onOpenProModal
}) => {
  const getInitialMessage = (lang: string): string => {
    switch (lang) {
      case 'en':
        return `👋 <b>Welcome to PaperFilterBot Academic Intelligence HQ!</b> 🤖\n\n🌐 <b>Live Connections</b>: Semantic Scholar (200M+), CrossRef, PubMed, arXiv & Google Drive.\n\n💡 <b>Highlights (Supports 4 Languages)</b>:\n• Direct search: Type any keyword (e.g. <code>CRISPR</code> or <code>Transformer</code>)\n• <code>/folders</code> or <code>my folders</code>: View & manage cloud folders\n• <code>add folder &lt;name&gt;</code>: Create new category folder\n• <code>rename &lt;old&gt; -&gt; &lt;new&gt;</code>: Rename category\n• <code>delete folder &lt;name&gt;</code>: Remove category\n• <code>/following</code> & <code>/follow &lt;name&gt;</code>: Track elite authors (+50 score bonus)\n• <code>/help</code>, <code>/bind</code>, <code>/pro</code>, <code>/mode</code>, <code>/lang</code>, <code>/review</code>, <code>/gap</code>, <code>/trend</code>\n\nType a command or click a quick prompt below to test!`;
      case 'ja':
        return `👋 <b>PaperFilterBot 学術インテリジェンス司令部へようこそ！</b> 🤖\n\n🌐 <b>接続データベース</b>：Semantic Scholar、CrossRef、PubMed、arXiv ＆ Google Drive\n\n💡 <b>主な機能（4ヶ国語コマンド対応）</b>：\n• キーワード直接検索（例：<code>CRISPR</code>、<code>Transformer</code>）\n• <code>/folders</code> または <code>マイフォルダ</code>：現在のカテゴリフォルダ一覧\n• <code>追加 フォルダ名</code>：新しいカテゴリフォルダの作成\n• <code>改名 旧 -&gt; 新</code>：フォルダ名の変更\n• <code>削除 フォルダ名</code>：フォルダの削除\n• <code>/following</code> ＆ <code>/follow 著者名</code>：注目著者を追跡（+50点優先推薦）\n• <code>/help</code>、<code>/bind</code>、<code>/pro</code>、<code>/lang</code>、<code>/mode</code>、<code>/review</code>、<code>/gap</code>\n\n下の入力欄からメッセージを送信またはクイックコマンドをお試しください！`;
      case 'zh_hans':
        return `👋 <b>欢迎使用 PaperFilterBot 学术智能雷达与云端文献库！</b> 🤖\n\n🌐 <b>全球 4 大官方库直连</b>：Semantic Scholar、CrossRef、PubMed、arXiv\n\n💡 <b>核心指令（全面支持中英日 4 国语言输入）</b>：\n• 直接发送关键词检索（如：<code>CRISPR</code> 或 <code>Transformer</code>）\n• <code>/folders</code> 或 <code>我的文件夹</code>：查看文献分类文件夹\n• <code>添加 文件夹名</code>：新建分类文件夹\n• <code>改名 旧 -&gt; 新</code>：重命名分类文件夹\n• <code>删除 文件夹名</code>：移除分类文件夹\n• <code>/following</code> 与 <code>/follow 学者名</code>：追踪重点学者（+50分加权）\n• <code>/help</code>、<code>/bind</code>、<code>/pro</code>、<code>/lang</code>、<code>/mode</code>、<code>/review</code>、<code>/gap</code>\n\n请在下方输入指令或点击快捷标签进行测试！`;
      default:
        return `👋 <b>歡迎使用 PaperFilterBot 學術智慧雷達與雲端文獻總庫！</b> 🤖\n\n🌐 <b>全球 4 大官方庫直連</b>：Semantic Scholar、CrossRef、PubMed、arXiv\n\n💡 <b>核心亮點（全面支援中英日 4 國語言指令輸入）</b>：\n• 直接傳送關鍵字搜尋論文（例如：<code>CRISPR</code> 或 <code>Transformer</code>）\n• <code>/folders</code> 或 <code>我的資料夾</code>：查看當前文獻分類資料夾\n• <code>新增 資料夾名</code> 或 <code>add folder 名稱</code>：建立新分類\n• <code>改名 舊 -&gt; 新</code> 或 <code>rename 舊 -&gt; 新</code>：更名資料夾\n• <code>刪除 資料夾名</code> 或 <code>delete folder 名稱</code>：移除分類\n• <code>/following</code> 與 <code>/follow 學者名</code>：追蹤重點學者（+50分加權）\n• <code>/help</code>、<code>/bind</code>、<code>/pro</code>、<code>/lang</code>、<code>/mode</code>、<code>/review</code>、<code>/gap</code>\n\n請在下方輸入指令或點擊快速標籤進行測試！`;
    }
  };

  const [messages, setMessages] = useState<BotMessage[]>([
    {
      id: '1',
      sender: 'bot',
      text: getInitialMessage(userLang),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSendMessage = async (textToSend?: string) => {
    const txt = (textToSend !== undefined ? textToSend : inputText).trim();
    if (!txt) return;

    const userMsg: BotMessage = {
      id: String(Date.now()),
      sender: 'user',
      text: txt,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (textToSend === undefined) setInputText('');
    setLoading(true);

    try {
      const res = await fetch('/api/simulate-bot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: txt, lang: userLang }),
      });
      const data = await res.json();

      // If command was language switch, update language in app
      if (data.switched_lang) {
        onLanguageChange(data.switched_lang);
      }

      const botReply: BotMessage = {
        id: String(Date.now() + 1),
        sender: 'bot',
        text: data.text || 'Error processing command',
        paper: data.paper,
        buttons: data.buttons,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, botReply]);
    } catch (err) {
      console.error('Bot simulator error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleButtonClick = (action: string, paper?: Paper) => {
    if (action === 'bind') {
      onOpenSyncModal();
      return;
    }
    if (action === 'pro') {
      onOpenProModal();
      return;
    }
    if (action.startsWith('lang_')) {
      const selectedLang = action.replace('lang_', '');
      onLanguageChange(selectedLang);
      handleSendMessage(`/lang ${selectedLang}`);
      return;
    }

    if (!paper) return;

    if (action === 'deep') {
      onOpenDeep(paper);
    } else if (action === 'archive' || action === 'seen') {
      onAddToLibrary(paper);
      const isSeen = action === 'seen';
      let confirmText = '';
      if (userLang === 'en') {
        confirmText = isSeen
          ? `👁️ <b>Marked as Seen</b> (+12 domain positive preference score):\n${paper.title}`
          : `✅ <b>Archived to 【${paper.category || 'AI'}】!</b>\n\n📄 Note embedded with BibTeX.\n📚 Synced to Google Drive <code>references.bib</code>!\n\n📌 ${paper.title}`;
      } else if (userLang === 'ja') {
        confirmText = isSeen
          ? `👁️ <b>既読に設定しました</b>（関心スコア +12点）：\n${paper.title}`
          : `✅ <b>【${paper.category || '人工知能'}】に保存しました！</b>\n\n📄 単一ノートに BibTeX を埋め込みました。\n📚 Google Drive の <code>references.bib</code> に同期しました！\n\n📌 ${paper.title}`;
      } else {
        confirmText = isSeen
          ? `👁️ <b>已標記為已讀</b>（保留此領域正向偏好 +12分）：\n${paper.title}`
          : `✅ 已成功歸檔至【<b>${paper.category || '人工智慧'}</b>】！\n\n📄 單篇筆記已內嵌 BibTeX\n📚 雲端 <code>references.bib</code> 引用總庫已同步追加！\n\n📌 ${paper.title}`;
      }

      setMessages(prev => [
        ...prev,
        {
          id: String(Date.now()),
          sender: 'bot',
          text: confirmText,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }
      ]);
    } else if (action === 'skip') {
      const skipText = userLang === 'en'
        ? `🗑 <b>Skipped paper</b> (Recommendation weight adjusted -6 pts):\n${paper.title}`
        : userLang === 'ja'
        ? `🗑 <b>スキップしました</b>（推薦スコア -6点）：\n${paper.title}`
        : `🗑 <b>已略過並減少此類推薦</b>（調降權重 -6分）：\n${paper.title}`;

      setMessages(prev => [
        ...prev,
        {
          id: String(Date.now()),
          sender: 'bot',
          text: skipText,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }
      ]);
    }
  };

  const quickGroups = [
    {
      title: '🌐 語言與說明 (Language & Help)',
      items: ['/help', '/lang', '/lang en', '/lang ja', '/lang zh_hant', '/start']
    },
    {
      title: '📂 資料夾指令 (4 語言支援: Folders / Add / Rename / Delete)',
      items: [
        '/folders',
        'my folders',
        'add folder Quantum Computing',
        'rename Quantum Computing -> Quantum AI',
        'delete folder Quantum AI',
        'マイフォルダ',
        '追加 ナノテクノロジー',
        '我的資料夾',
        '新增 量子計算'
      ]
    },
    {
      title: '👥 學者追蹤 (Follow / Track Authors)',
      items: ['/following', '/follow Yann LeCun', 'follow Geoffrey Hinton', 'フォロー Jennifer Doudna', '追蹤 Kaiming He']
    },
    {
      title: '🔬 旗艦科研與檢索 (Pro & Search)',
      items: ['/pro', '/bind', '/mode', '/review', '/gap', 'CRISPR Cas9', 'Attention Transformer']
    }
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      {/* Bot Header Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex items-center justify-between shadow-lg">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-white font-bold text-xl shadow-md">
            🤖
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="font-bold text-white text-sm">PaperFilterBot (@paper_filter_bot)</h3>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            </div>
            <p className="text-xs text-slate-400 font-mono">
              Telegram 雙向同步中 · 4 國語言指令支援 (ZH/EN/JA)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Quick Language Toggle */}
          <div className="flex items-center bg-slate-800 rounded-lg p-0.5 border border-slate-700 text-xs">
            <Globe className="w-3.5 h-3.5 text-slate-400 ml-1.5 mr-1" />
            <select
              value={userLang}
              onChange={(e) => {
                const newLang = e.target.value;
                onLanguageChange(newLang);
                handleSendMessage(`/lang ${newLang}`);
              }}
              className="bg-transparent text-slate-200 text-xs px-1.5 py-1 focus:outline-none cursor-pointer"
            >
              <option value="zh_hant" className="bg-slate-900 text-slate-100">繁體中文</option>
              <option value="en" className="bg-slate-900 text-slate-100">English</option>
              <option value="ja" className="bg-slate-900 text-slate-100">日本語</option>
              <option value="zh_hans" className="bg-slate-900 text-slate-100">简体中文</option>
            </select>
          </div>

          <button
            onClick={onOpenSyncModal}
            className="flex items-center space-x-1 text-xs text-sky-300 hover:text-white px-2.5 py-1.5 bg-sky-950/60 hover:bg-sky-900/60 rounded-lg border border-sky-500/40 transition-colors cursor-pointer"
          >
            <LinkIcon className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">同步代碼</span>
          </button>

          <button
            onClick={() => setMessages([{ id: String(Date.now()), sender: 'bot', text: getInitialMessage(userLang), timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }])}
            className="flex items-center space-x-1 text-xs text-slate-400 hover:text-white px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 transition-colors cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>重置</span>
          </button>
        </div>
      </div>

      {/* Chat messages viewport */}
      <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 sm:p-6 min-h-[480px] max-h-[580px] overflow-y-auto space-y-4 shadow-inner">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start gap-3 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.sender === 'bot' && (
              <div className="w-8 h-8 rounded-lg bg-indigo-600/80 text-white flex items-center justify-center text-sm shrink-0 mt-0.5 shadow-sm">
                🤖
              </div>
            )}

            <div
              className={`max-w-xl rounded-2xl p-4 text-xs sm:text-sm leading-relaxed shadow-md space-y-3 ${
                msg.sender === 'user'
                  ? 'bg-indigo-600 text-white rounded-br-none'
                  : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none'
              }`}
            >
              <div
                className="whitespace-pre-line break-words"
                dangerouslySetInnerHTML={{ __html: msg.text }}
              />

              {/* Inline Keyboard Buttons */}
              {msg.buttons && msg.buttons.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-slate-800/80">
                  {msg.buttons.map((btn, bidx) => (
                    <button
                      key={bidx}
                      onClick={() => handleButtonClick(btn.action, msg.paper)}
                      className="px-3 py-2 bg-slate-800 hover:bg-indigo-700 text-slate-200 hover:text-white rounded-lg text-xs font-medium border border-slate-700 transition-all text-center cursor-pointer shadow-sm"
                    >
                      {btn.label}
                    </button>
                  ))}
                </div>
              )}

              <div className={`text-[10px] text-right ${msg.sender === 'user' ? 'text-indigo-200' : 'text-slate-500'}`}>
                {msg.timestamp}
              </div>
            </div>

            {msg.sender === 'user' && (
              <div className="w-8 h-8 rounded-lg bg-slate-800 text-slate-300 flex items-center justify-center text-sm shrink-0 mt-0.5 border border-slate-700">
                <User className="w-4 h-4" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-center space-x-2 text-slate-400 text-xs pl-11">
            <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
            <span>PaperFilterBot 正在分析指令並跨庫連線中...</span>
          </div>
        )}

        <div ref={scrollRef} />
      </div>

      {/* Categorized Quick Command Testing Chips */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3 space-y-2.5">
        <div className="text-xs font-semibold text-slate-300 flex items-center justify-between">
          <span>⚡ 快速指令測試區（點擊即可在機器人中執行）：</span>
          <span className="text-[11px] text-emerald-400">支援 /folders, add folder, rename, /following 等</span>
        </div>

        {quickGroups.map((group, idx) => (
          <div key={idx} className="space-y-1.5">
            <div className="text-[11px] text-slate-400 font-medium">{group.title}</div>
            <div className="flex flex-wrap gap-1.5">
              {group.items.map((cmd) => (
                <button
                  key={cmd}
                  onClick={() => handleSendMessage(cmd)}
                  className="text-xs font-mono px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-indigo-300 hover:text-white border border-slate-700 transition-colors cursor-pointer"
                >
                  {cmd}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Input box */}
      <form onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }} className="flex items-center space-x-2">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={
            userLang === 'en'
              ? 'Type /folders, add folder AI, /follow Hinton, /help, /pro, or paper keywords...'
              : userLang === 'ja'
              ? 'コマンド /folders、追加 ナノ、/follow 著者名、/help または論文キーワードを入力...'
              : '輸入 /folders, add folder 量子, /follow 作者名, /help, /pro 或學術關鍵字...'
          }
          className="flex-1 px-4 py-3 bg-slate-900 border border-slate-700 rounded-xl text-white placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500"
        />
        <button
          type="submit"
          disabled={!inputText.trim() || loading}
          className="px-5 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition-colors flex items-center space-x-1.5 shadow-md shadow-indigo-600/30 disabled:opacity-50 cursor-pointer"
        >
          <Send className="w-4 h-4" />
          <span className="hidden sm:inline">傳送</span>
        </button>
      </form>
    </div>
  );
};
