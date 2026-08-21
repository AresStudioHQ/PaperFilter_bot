import React, { useState } from 'react';
import { Bot, Link as LinkIcon, CheckCircle2, Copy, Check } from 'lucide-react';
import { UserProfile } from '../types';
import { useI18n } from '../i18n';

interface TelegramBindingModalProps {
  user: UserProfile;
  isOpen: boolean;
  onClose: () => void;
  onBindSuccess: (updatedUser: UserProfile) => void;
}

export const TelegramBindingModal: React.FC<TelegramBindingModalProps> = ({
  user,
  isOpen,
  onClose,
  onBindSuccess
}) => {
  const { t } = useI18n();
  const [syncCodeInput, setSyncCodeInput] = useState(user.sync_code || '');
  const [handleInput, setHandleInput] = useState(user.telegram_handle || '@ares_researcher');
  const [copiedCode, setCopiedCode] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleCopyCode = () => {
    navigator.clipboard.writeText(user.sync_code || 'PF8892');
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const handleBind = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const res = await fetch('/api/auth/bind-telegram', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: syncCodeInput, telegram_handle: handleInput })
      });
      const data = await res.json();
      if (data.success) {
        setSuccessMsg(data.message);
        onBindSuccess(data.user);
        setTimeout(() => {
          setSuccessMsg(null);
          onClose();
        }, 1500);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-slate-900 border border-slate-700 rounded-3xl max-w-lg w-full p-6 sm:p-8 shadow-2xl space-y-6 relative overflow-hidden">
        
        {/* Glow */}
        <div className="absolute -right-20 -top-20 w-60 h-60 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-sky-500/20 text-sky-400 flex items-center justify-center border border-sky-500/30">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">{t('bind_modal_title')}</h3>
              <p className="text-xs text-slate-400">{t('bind_modal_subtitle')}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white text-lg p-1 cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Steps Guide */}
        <div className="bg-slate-950/70 p-4 rounded-2xl border border-slate-800 space-y-3 text-xs text-slate-300">
          <div className="flex items-start gap-2.5">
            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white font-bold flex items-center justify-center text-[10px] shrink-0">1</span>
             <span>{t('step1_title')}</span>
          </div>
          <div className="flex items-start gap-2.5">
            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white font-bold flex items-center justify-center text-[10px] shrink-0">2</span>
             <span>{t('step2_desc')}</span>
          </div>
          <div className="flex items-start gap-2.5">
            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white font-bold flex items-center justify-center text-[10px] shrink-0">3</span>
             <span>{t('step3_desc')}</span>
          </div>
        </div>

        {/* Dynamic Code Card */}
        <div className="flex items-center justify-between p-4 rounded-2xl bg-slate-800/60 border border-slate-700">
          <div>
            <span className="text-[11px] text-slate-400 block">{t('bind_current_code')}</span>
            <span className="text-2xl font-mono font-extrabold text-sky-400 tracking-wider">
              {user.sync_code || 'PF8892'}
            </span>
          </div>
          <button
            onClick={handleCopyCode}
            className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            {copiedCode ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
            <span>{copiedCode ? t('bind_copied') : t('bind_copy_code')}</span>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleBind} className="space-y-4">
          <div>
            <label className="text-xs text-slate-300 font-semibold block mb-1.5">
              {t('bind_handle_label')}
            </label>
            <input
              type="text"
              value={handleInput}
              onChange={(e) => setHandleInput(e.target.value)}
              placeholder="@your_telegram_username"
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
            />
          </div>

          <div>
            <label className="text-xs text-slate-300 font-semibold block mb-1.5">
              {t('step3_title')}
            </label>
            <input
              type="text"
              value={syncCodeInput}
              onChange={(e) => setSyncCodeInput(e.target.value)}
              placeholder={t('sync_code_placeholder')}
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 font-mono focus:outline-none focus:border-sky-500"
            />
          </div>

          {successMsg && (
            <div className="p-3 bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 text-xs rounded-xl flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" />
              <span>{successMsg}</span>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold cursor-pointer"
            >
              {t('btn_cancel')}
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 py-2.5 bg-sky-500 hover:bg-sky-600 text-white rounded-xl text-xs font-bold shadow-lg shadow-sky-500/20 transition-all flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <LinkIcon className="h-3.5 w-3.5" />
               <span>{isLoading ? t('bind_verifying') : t('btn_confirm_sync')}</span>
            </button>
          </div>
        </form>

      </div>
    </div>
  );
};
