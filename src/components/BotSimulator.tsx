import React, { useState, useRef, useEffect } from 'react';
import { Send, User, RefreshCw, Link as LinkIcon, Globe, FolderPlus, ListOrdered, UserPlus, HelpCircle } from 'lucide-react';
import { BotMessage, Paper } from '../types';
import { useI18n, localeFromLang } from '../i18n';

interface BotSimulatorProps {
  userLang: string;
  botUsername?: string;
  onLanguageChange: (lang: string) => void;
  onOpenDeep: (paper: Paper) => void;
  onAddToLibrary: (paper: Paper) => void;
  onOpenSyncModal: () => void;
  onOpenProModal: () => void;
}

export const BotSimulator: React.FC<BotSimulatorProps> = ({ 
  userLang,
  botUsername = 'paper_filter_bot',
  onLanguageChange,
  onOpenDeep, 
  onAddToLibrary,
  onOpenSyncModal,
  onOpenProModal
}) => {
  const { t } = useI18n(userLang);
  const tgUrl = `https://t.me/${String(botUsername).replace(/^@/, '')}`;
  const clock = () => new Date().toLocaleTimeString(localeFromLang(userLang), { hour: '2-digit', minute: '2-digit' });

  const [messages, setMessages] = useState<BotMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const loadStart = async () => {
    try {
      const res = await fetch('/api/simulate-bot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: '/start', lang: userLang }),
      });
      const data = await res.json();
      setMessages([{
        id: String(Date.now()),
        sender: 'bot',
        text: data.text || '',
        buttons: data.buttons,
        timestamp: clock(),
      }]);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadStart();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
      timestamp: clock(),
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
        timestamp: clock(),
      };
      setMessages((prev) => [...prev, botReply]);
    } catch (err) {
      console.error('Bot simulator error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleButtonClick = (action: string, paper?: Paper, url?: string) => {
    if (action === 'open_telegram') {
      window.open(tgUrl, '_blank', 'noopener,noreferrer');
      return;
    }
    if (action === 'bind') {
      onOpenSyncModal();
      return;
    }
    if (action === 'pro') {
      onOpenProModal();
      return;
    }
    if (action === 'help') {
      handleSendMessage('/help');
      return;
    }
    if (action.startsWith('search:')) {
      handleSendMessage(action.slice('search:'.length));
      return;
    }
    if (action.startsWith('mode:')) {
      handleSendMessage(`/mode ${action.slice('mode:'.length)}`);
      return;
    }
    if (action.startsWith('lang_')) {
      const selectedLang = action.replace('lang_', '');
      onLanguageChange(selectedLang);
      handleSendMessage(`/lang ${selectedLang}`);
      return;
    }
    if (action === 'oa' || action === 'doi') {
      const href = url || paper?.link;
      if (href) window.open(href, '_blank', 'noopener,noreferrer');
      return;
    }

    if (!paper) return;

    if (action === 'deep') {
      onOpenDeep(paper);
    } else if (action === 'archive' || action === 'seen') {
      onAddToLibrary(paper);
      const isSeen = action === 'seen';
      const confirmText = isSeen
        ? `👁️ <b>${t('sim_seen_marked')}</b>\n${paper.title}`
        : `✅ <b>${t('sim_archive_success', { cat: paper.category || 'AI' })}</b>\n📌 ${paper.title}`;

      setMessages(prev => [
        ...prev,
        {
          id: String(Date.now()),
          sender: 'bot',
          text: confirmText,
          timestamp: clock(),
        }
      ]);
    } else if (action === 'skip') {
      setMessages(prev => [
        ...prev,
        {
          id: String(Date.now()),
          sender: 'bot',
          text: `🗑 <b>${t('sim_skip_marked')}</b>\n${paper.title}`,
          timestamp: clock(),
        }
      ]);
    }
  };

  const quickGroups = [
    {
      titleKey: 'sim_quick_group_lang',
      items: ['/help', '/lang', '/lang en', '/lang ja', '/lang zh_hant', '/start']
    },
    {
      titleKey: 'sim_quick_group_folders',
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
      titleKey: 'sim_quick_group_scholars',
      items: ['/following', '/follow Yann LeCun', 'follow Geoffrey Hinton', 'フォロー Jennifer Doudna', '追蹤 Kaiming He']
    },
    {
      titleKey: 'sim_quick_group_flagship',
      items: ['/pro', '/bind', '/web', '/mode', '/review', '/gap', 'CRISPR Cas9', 'Attention Transformer']
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
              <h3 className="font-bold text-white text-sm">PaperFilterBot (@{botUsername.replace(/^@/, '')})</h3>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            </div>
            <p className="text-xs text-slate-400 font-mono">
              {t('sim_sync_status')}
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
            <span className="hidden sm:inline">{t('sim_sync_code')}</span>
          </button>

          <button
            onClick={() => loadStart()}
            className="flex items-center space-x-1 text-xs text-slate-400 hover:text-white px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 transition-colors cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{t('sim_btn_reset')}</span>
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
                      onClick={() => handleButtonClick(btn.action, msg.paper, btn.url)}
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
            <span>{t('sim_loading')}</span>
          </div>
        )}

        <div ref={scrollRef} />
      </div>

      {/* Categorized Quick Command Testing Chips */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3 space-y-2.5">
        <div className="text-xs font-semibold text-slate-300 flex items-center justify-between">
          <span>{t('sim_quick_test_label')}</span>
          <span className="text-[11px] text-emerald-400">{t('sim_quick_test_hint')}</span>
        </div>

        {quickGroups.map((group, idx) => (
          <div key={idx} className="space-y-1.5">
            <div className="text-[11px] text-slate-400 font-medium">{t(group.titleKey)}</div>
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
          placeholder={t('sim_input_placeholder')}
          className="flex-1 px-4 py-3 bg-slate-900 border border-slate-700 rounded-xl text-white placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500"
        />
        <button
          type="submit"
          disabled={!inputText.trim() || loading}
          className="px-5 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition-colors flex items-center space-x-1.5 shadow-md shadow-indigo-600/30 disabled:opacity-50 cursor-pointer"
        >
          <Send className="w-4 h-4" />
          <span className="hidden sm:inline">{t('sim_btn_send')}</span>
        </button>
      </form>
    </div>
  );
};
