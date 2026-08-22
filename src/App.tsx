import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { DashboardOverview } from './components/DashboardOverview';
import { LibraryManagement } from './components/LibraryManagement';
import { SearchSection } from './components/SearchSection';
import { ProFeaturesHub } from './components/ProFeaturesHub';
import { DeepModal } from './components/DeepModal';
import { TelegramBindingModal } from './components/TelegramBindingModal';
import { Paper, UserProfile, FilterMode, HistoryRecord } from './types';
import { useI18n, Language } from './i18n';
import './_i18n_tier';
import { TelegramLogin } from './TelegramLogin';
import { BrainCircuit, X, Copy, Check } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [user, setUser] = useState<UserProfile>({
    user_id: 0,
    username: '',
    telegram_handle: '',
    is_telegram_linked: false,
    sync_code: '',
    tier: 'free',
    filter_mode: 'smart',
    user_lang: 'en',
    total_read_count: 0,
    total_archived_count: 0,
    total_skipped_count: 0,
    total_deep_read_count: 0,
  });
  const { t } = useI18n(user.user_lang);
  const [categories, setCategories] = useState<string[]>([]);
  const [followedAuthors, setFollowedAuthors] = useState<string[]>([]);
  const [library, setLibrary] = useState<Paper[]>([]);
  const [history, setHistory] = useState<HistoryRecord[]>([]);

  // 多使用者登入狀態
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [botUsername, setBotUsername] = useState<string>('');

  // 深度導讀
  const [deepPaper, setDeepPaper] = useState<Paper | null>(null);
  const [deepReport, setDeepReport] = useState<string>('');
  const [bibtex, setBibtex] = useState<string>('');
  const [loadingDeep, setLoadingDeep] = useState(false);

  // 文獻綜述 / 缺口 結果彈窗
  const [reviewModalData, setReviewModalData] = useState<{ title: string; content: string } | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [copiedReview, setCopiedReview] = useState(false);

  const [isSyncModalOpen, setIsSyncModalOpen] = useState(false);

  // 載入使用者專屬資料（登入後呼叫）
  const loadData = () => {
    fetch('/api/library').then(r => r.json()).then(d => { if (d.success) setLibrary(d.library || []); }).catch(console.error);
    fetch('/api/history').then(r => r.json()).then(d => { if (d.success) setHistory(d.history || []); }).catch(console.error);
  };

  const refreshUser = () => {
    fetch('/api/auth/profile').then(r => r.json()).then(d => {
      if (d.success && d.user) {
        setUser(d.user);
        setCategories(d.categories || []);
        setFollowedAuthors(d.followed_authors || []);
      }
    }).catch(() => {});
  };

  // 初次載入：先檢查登入狀態
  useEffect(() => {
    fetch('/api/auth/config').then(r => r.json()).then(d => { if (d.success) setBotUsername(d.bot_username); }).catch(() => {});
    fetch('/api/auth/profile').then(res => res.json().then(data => ({ res, data }))).then(({ res, data }) => {
      if (res.status === 401 && data.loginRequired) { setAuthed(false); return; }
      if (data.success && data.user) {
        setUser(data.user);
        setCategories(data.categories || []);
        setFollowedAuthors(data.followed_authors || []);
        setAuthed(true);
        loadData();
      } else {
        setAuthed(false);
      }
    }).catch(() => setAuthed(false));
  }, []);

  const handleLoggedIn = () => {
    fetch('/api/auth/profile').then(r => r.json()).then(d => {
      if (d.success && d.user) {
        setUser(d.user);
        setCategories(d.categories || []);
        setFollowedAuthors(d.followed_authors || []);
        setAuthed(true);
        loadData();
      } else {
        setAuthed(false);
      }
    }).catch(() => setAuthed(false));
  };

  const handleOpenDeep = async (paper: Paper) => {
    setDeepPaper(paper);
    setLoadingDeep(true);
    setDeepReport('');
    setBibtex('');
    try {
      const res = await fetch('/api/deep', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...paper }),
      });
      const data = await res.json();
      if (data.success) {
        setDeepReport(data.deep_report);
        setBibtex(data.bibtex);
        fetch('/api/history').then(r => r.json()).then(d => d.success && setHistory(d.history));
      } else {
        setDeepReport(data.error || t('app_deep_error'));
      }
    } catch (err) {
      console.error('Deep read error:', err);
    } finally {
      setLoadingDeep(false);
    }
  };

  const handleAddToLibrary = async (paper: Paper, targetCategory?: string) => {
    try {
      const cat = targetCategory || paper.category || categories[0] || t('app_cat_ai');
      const res = await fetch('/api/library/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...paper, category: cat }),
      });
      const data = await res.json();
      if (data.success && data.paper) {
        setLibrary(prev => {
          const idx = prev.findIndex(p => p.id === data.paper.id || p.fingerprint === data.paper.fingerprint);
          if (idx >= 0) {
            const updated = [...prev];
            updated[idx] = data.paper;
            return updated;
          }
          return [data.paper, ...prev];
        });
        fetch('/api/history').then(r => r.json()).then(d => d.success && setHistory(d.history));
      }
    } catch (err) {
      console.error('Add to library error:', err);
    }
  };

  const handleRemoveFromLibrary = async (paperId: string) => {
    try {
      await fetch(`/api/library/${paperId}`, { method: 'DELETE' });
      setLibrary(prev => prev.filter(p => p.id !== paperId && p.fingerprint !== paperId));
    } catch (err) {
      console.error('Remove paper error:', err);
    }
  };

  const handleUpdateNotes = async (paperId: string, notes: string, tags?: string[], isStarred?: boolean) => {
    try {
      const res = await fetch('/api/library/update-paper', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: paperId, user_notes: notes, tags, is_starred: isStarred }),
      });
      const data = await res.json();
      if (data.success && data.paper) {
        setLibrary(prev => prev.map(p => (p.id === data.paper.id ? data.paper : p)));
      }
    } catch (err) {
      console.error('Update paper error:', err);
    }
  };

  const handleCategoryAction = async (action: 'add' | 'rename' | 'delete', payload: { name?: string; oldName?: string; newName?: string }) => {
    try {
      const res = await fetch('/api/categories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, ...payload }),
      });
      const data = await res.json();
      if (data.success) setCategories(data.categories);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAuthorAction = async (action: 'add' | 'remove', name: string) => {
    try {
      const res = await fetch('/api/authors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, name }),
      });
      const data = await res.json();
      if (data.success) setFollowedAuthors(data.followed_authors);
    } catch (err) {
      console.error(err);
    }
  };

  const handleFilterModeChange = async (mode: FilterMode) => {
    try {
      const res = await fetch('/api/auth/update-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      });
      const data = await res.json();
      if (data.success) setUser(prev => ({ ...prev, filter_mode: data.mode || mode }));
    } catch (err) {
      console.error(err);
    }
  };

  const handleLanguageChange = async (lang: string) => {
    try {
      const res = await fetch('/api/user/language', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lang }),
      });
      const data = await res.json();
      if (data.success) setUser(prev => ({ ...prev, user_lang: data.lang || lang }));
    } catch (err) {
      console.error(err);
    }
  };

  const handleTriggerReview = async (papers: Paper[] = library) => {
    setReviewLoading(true);
    setReviewModalData({ title: t('app_review_title'), content: t('app_review_loading') });
    try {
      const res = await fetch('/api/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ papers }),
      });
      const data = await res.json();
      if (data.success) {
        setReviewModalData({ title: t('app_review_title_count', { count: data.paper_count }), content: data.review });
      } else {
        setReviewModalData({ title: t('app_ai_error_title'), content: data.error || t('app_ai_service_unavailable') });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setReviewLoading(false);
    }
  };

  const handleTriggerGap = async (papers: Paper[] = library) => {
    setReviewLoading(true);
    setReviewModalData({ title: t('app_gap_title'), content: t('app_gap_loading') });
    try {
      const res = await fetch('/api/gap', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ papers }),
      });
      const data = await res.json();
      if (data.success) {
        setReviewModalData({ title: t('app_gap_title_done'), content: data.gap_analysis });
      } else {
        setReviewModalData({ title: t('app_ai_error_title'), content: data.error || t('app_ai_service_unavailable') });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setReviewLoading(false);
    }
  };

  const handleTriggerMatrix = (papers: Paper[]) => {
    setActiveTab('pro');
  };

  const handleRedeemCode = async (code: string) => {
    const res = await fetch('/api/auth/redeem', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });
    const data = await res.json();
    if (data.success && data.user) {
      setUser(data.user);
      return;
    }
    throw new Error(data.error || t('pro_redeem_fail'));
  };

  // ---------- 登入閘門 ----------
  if (authed === null) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-300 flex items-center justify-center">
        {t('app_loading')}
      </div>
    );
  }
  if (authed === false) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
        <div className="bg-slate-900 border border-slate-700 rounded-3xl p-8 max-w-md w-full text-center space-y-5">
          <h1 className="text-xl font-bold text-white">{t('app_login_title')}</h1>
          <p className="text-sm text-slate-400">{t('app_login_desc')}</p>
          <TelegramLogin botUsername={botUsername} userLang={user.user_lang as Language} onLoggedIn={handleLoggedIn} />
          {!botUsername && (
            <p className="text-xs text-slate-500">{t('app_login_no_button')}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        user={user}
        onOpenSyncModal={() => setIsSyncModalOpen(true)}
        onOpenProModal={() => setActiveTab('pro')}
        filterMode={user.filter_mode}
        onFilterModeChange={handleFilterModeChange}
        userLang={user.user_lang}
        onLanguageChange={handleLanguageChange}
        libraryCount={library.length}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'dashboard' && (
          <DashboardOverview
            user={user}
            categories={categories}
            followedAuthors={followedAuthors}
            library={library}
            history={history}
            userLang={user.user_lang}
            onOpenDeep={handleOpenDeep}
            onSelectPaperForDeep={handleOpenDeep}
            onOpenSyncModal={() => setIsSyncModalOpen(true)}
            onOpenProModal={() => setActiveTab('pro')}
            onAddAuthor={(a) => handleAuthorAction('add', a)}
            onRemoveAuthor={(a) => handleAuthorAction('remove', a)}
            onNavigateToTab={(tab) => setActiveTab(tab)}
          />
        )}

        {activeTab === 'library' && (
          <LibraryManagement
            library={library}
            categories={categories}
            userLang={user.user_lang}
            onAddCategory={(n) => handleCategoryAction('add', { name: n })}
            onDeleteCategory={(n) => handleCategoryAction('delete', { name: n })}
            onDeletePaper={handleRemoveFromLibrary}
            onUpdatePaper={(p) => handleUpdateNotes(p.id, p.user_notes || '', p.tags, p.is_starred)}
            onSelectPaperForDeep={handleOpenDeep}
            onTriggerReview={handleTriggerReview}
            onTriggerGap={handleTriggerGap}
            onTriggerMatrix={handleTriggerMatrix}
          />
        )}

        {activeTab === 'search' && (
          <SearchSection
            filterMode={user.filter_mode}
            categories={categories}
            userLang={user.user_lang}
            onAddToLibrary={handleAddToLibrary}
            onOpenDeep={handleOpenDeep}
            libraryPaperIds={library.map(p => p.id)}
          />
        )}

        {activeTab === 'pro' && (
          <ProFeaturesHub
            library={library}
            user={user}
            userLang={user.user_lang}
            onRedeemCode={handleRedeemCode}
            onSelectPaperForDeep={handleOpenDeep}
          />
        )}

      </main>

      <DeepModal
        paper={deepPaper}
        deepReport={deepReport}
        bibtex={bibtex}
        loading={loadingDeep}
        userLang={user.user_lang}
        onClose={() => setDeepPaper(null)}
        onAddToLibrary={handleAddToLibrary}
        isArchived={library.some(p => p.id === deepPaper?.id)}
      />

      {isSyncModalOpen && (
        <TelegramBindingModal
          user={user}
          isOpen={isSyncModalOpen}
          onClose={() => setIsSyncModalOpen(false)}
          onBindSuccess={() => { refreshUser(); loadData(); }}
        />
      )}

      {reviewModalData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-700 rounded-3xl max-w-3xl w-full p-6 sm:p-8 shadow-2xl space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <BrainCircuit className="h-5 w-5 text-indigo-400" />
                <span>{reviewModalData.title}</span>
              </h3>
              <button onClick={() => setReviewModalData(null)} className="text-slate-400 hover:text-white p-1">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto pr-2 bg-slate-950 p-5 rounded-2xl border border-slate-800 text-xs sm:text-sm text-slate-200 leading-relaxed whitespace-pre-wrap font-sans">
              {reviewModalData.content}
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-800">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(reviewModalData.content);
                  setCopiedReview(true);
                  setTimeout(() => setCopiedReview(false), 2000);
                }}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-md"
              >
                {copiedReview ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                <span>{copiedReview ? t('app_copied_full') : t('app_copy_markdown')}</span>
              </button>

              <button
                onClick={() => setReviewModalData(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold"
              >
                {t('app_close')}
              </button>
            </div>
          </div>
        </div>
      )}

      <footer className="border-t border-slate-800/80 bg-slate-900/50 py-5 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <p>{t('footer_hq')}</p>
          <p className="font-mono text-indigo-400">PaperFilterBot · Free / Pro</p>
        </div>
      </footer>
    </div>
  );
}
