import React from 'react';
import { 
  Sparkles, 
  Library, 
  Search, 
  LayoutDashboard, 
  Crown, 
  Link as LinkIcon,
  CheckCircle2
} from 'lucide-react';
import { UserProfile, FilterMode } from '../types';
import { useI18n } from '../i18n';
import { hasPaidTier } from '../subscriptionTiers';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  user: UserProfile;
  onOpenSyncModal: () => void;
  onOpenProModal: () => void;
  filterMode: FilterMode;
  onFilterModeChange: (mode: FilterMode) => void;
  userLang: string;
  onLanguageChange: (lang: string) => void;
  libraryCount: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  user,
  onOpenSyncModal,
  onOpenProModal,
  filterMode,
  onFilterModeChange,
  userLang,
  onLanguageChange,
  libraryCount,
}) => {
  const { t } = useI18n(userLang);

  return (
    <header className="sticky top-0 z-40 bg-slate-900/95 backdrop-blur-md border-b border-slate-800 text-slate-100 w-full shadow-lg shadow-black/25">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Tier 1: Brand & Global Control Actions */}
        <div className="flex items-center justify-between h-14 sm:h-16 gap-3 min-w-0">
          
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3 cursor-pointer shrink-0" onClick={() => setActiveTab('dashboard')}>
            <div className="h-9 w-9 sm:h-10 sm:w-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-blue-500 to-cyan-400 flex items-center justify-center shadow-md ring-1 ring-white/20 shrink-0">
              <Sparkles className="h-4 w-4 sm:h-5 sm:w-5 text-white animate-pulse" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center space-x-1.5">
                <span className="font-bold text-base sm:text-lg tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-300 bg-clip-text text-transparent">
                  {t('brand_title')}
                </span>
                <span className="px-1.5 py-0.2 text-[10px] font-semibold rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 shrink-0">
                  {t('brand_hq_suffix')}
                </span>
              </div>
              <p className="hidden md:block text-[11px] text-slate-400 font-medium truncate max-w-sm">
                {t('brand_sub')}
              </p>
            </div>
          </div>

          {/* Right Action Bar */}
          <div className="flex items-center space-x-2 sm:space-x-2.5 shrink-0">
            
            {/* Filter Mode Selector */}
            <div className="hidden sm:flex items-center bg-slate-800/90 rounded-lg p-0.5 border border-slate-700 text-xs shrink-0">
              <button
                onClick={() => onFilterModeChange('smart')}
                className={`px-2 py-1 rounded transition-colors whitespace-nowrap ${
                  filterMode === 'smart' ? 'bg-indigo-600 text-white font-medium shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Smart balance based on citations, recency and user bias"
              >
                {t('mode_smart')}
              </button>
              <button
                onClick={() => onFilterModeChange('top_tier')}
                className={`px-2 py-1 rounded transition-colors whitespace-nowrap ${
                  filterMode === 'top_tier' ? 'bg-indigo-600 text-white font-medium shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Top-tier venues priority (Nature, Science, NeurIPS, etc.)"
              >
                {t('mode_top_tier')}
              </button>
              <button
                onClick={() => onFilterModeChange('free_only')}
                className={`px-2 py-1 rounded transition-colors whitespace-nowrap ${
                  filterMode === 'free_only' ? 'bg-indigo-600 text-white font-medium shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Only Open Access papers with free fulltext PDF"
              >
                {t('mode_free_only')}
              </button>
            </div>

            {/* Language Selector Dropdown */}
            <div className="flex items-center bg-slate-800/90 rounded-lg px-1.5 py-0.5 border border-slate-700 text-xs shrink-0 shadow-sm">
              <select
                value={userLang}
                onChange={(e) => onLanguageChange(e.target.value)}
                className="bg-transparent text-slate-200 text-xs py-1 px-1 focus:outline-none cursor-pointer font-medium"
              >
                <option value="zh_hant" className="bg-slate-900 text-slate-100">🇹🇼 {t('nav_lang_zh_hant')}</option>
                <option value="zh_hans" className="bg-slate-900 text-slate-100">🇨🇳 {t('nav_lang_zh_hans')}</option>
                <option value="en" className="bg-slate-900 text-slate-100">🇺🇸 EN</option>
                <option value="ja" className="bg-slate-900 text-slate-100">🇯🇵 {t('nav_lang_ja')}</option>
              </select>
            </div>

            {/* Telegram Link Status Badge */}
            <button
              onClick={onOpenSyncModal}
              className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-all shrink-0 ${
                user.is_telegram_linked
                  ? 'bg-sky-950/60 border-sky-500/40 text-sky-300 hover:bg-sky-900/60'
                  : 'bg-amber-950/60 border-amber-500/40 text-amber-300 hover:bg-amber-900/60 animate-pulse'
              }`}
            >
              {user.is_telegram_linked ? (
                <>
                  <CheckCircle2 className="h-3.5 w-3.5 text-sky-400 shrink-0" />
                  <span className="hidden md:inline">{user.telegram_handle || t('tg_linked')}</span>
                  <span className="md:hidden">{t('tg_linked')}</span>
                </>
              ) : (
                <>
                  <LinkIcon className="h-3.5 w-3.5 shrink-0" />
                  <span>{t('tg_bind')}</span>
                </>
              )}
            </button>

            {/* Pro Tier Button */}
            <button
              onClick={onOpenProModal}
              className={`flex items-center space-x-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all shadow-md shrink-0 ${
                hasPaidTier(user.tier)
                  ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:from-amber-600 hover:to-orange-600 ring-1 ring-amber-400/40'
                  : 'bg-slate-800 text-amber-300 border border-amber-500/40 hover:bg-amber-500/10'
              }`}
            >
              <Crown className="h-3.5 w-3.5 shrink-0" />
              <span className="whitespace-nowrap">{hasPaidTier(user.tier) ? `👑 ${t('pro_badge')}` : t('upgrade_pro')}</span>
            </button>

          </div>

        </div>

        {/* Tier 2: Unified Tab Navigation (All 8 Modules with smooth overflow scroll & active states) */}
        <div className="flex items-center space-x-1.5 sm:space-x-2 overflow-x-auto py-2.5 border-t border-slate-800/80 scrollbar-none">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all whitespace-nowrap shrink-0 ${
              activeTab === 'dashboard'
                ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/50 shadow-inner font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <LayoutDashboard className="h-4 w-4 shrink-0" />
            <span>{t('nav_dashboard')}</span>
          </button>

          <button
            onClick={() => setActiveTab('library')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all whitespace-nowrap shrink-0 relative ${
              activeTab === 'library'
                ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/50 shadow-inner font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Library className="h-4 w-4 shrink-0" />
            <span>{t('nav_library')}</span>
            {libraryCount > 0 && (
              <span className="ml-1 px-1.5 py-0.2 text-[10px] font-bold rounded-full bg-indigo-500 text-white shrink-0">
                {libraryCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('search')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all whitespace-nowrap shrink-0 ${
              activeTab === 'search'
                ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/50 shadow-inner font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Search className="h-4 w-4 shrink-0" />
            <span>{t('nav_search')}</span>
          </button>

          <button
            onClick={() => setActiveTab('pro')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all whitespace-nowrap shrink-0 text-amber-300 ${
              activeTab === 'pro'
                ? 'bg-amber-500/25 text-amber-200 border border-amber-500/50 shadow-inner font-semibold'
                : 'hover:text-amber-200 hover:bg-amber-500/10'
            }`}
          >
            <Crown className="h-4 w-4 text-amber-400 shrink-0" />
            <span>{t('nav_pro')}</span>
          </button>

        </div>

      </div>
    </header>
  );
};
