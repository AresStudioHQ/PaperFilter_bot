// 訂閱等級單一資料源：數值與 bot 端 database.py 的 TIER_DEFS / TIER_PRICES / TIER_RANK 完全一致。
// 前端 Pro 專區與 Navbar 都從這裡讀，避免前後端額度不同步。

export type TierCode = 'free' | 'basic' | 'standard' | 'premium' | 'ultra' | 'lab';

export const UNLIMITED = 999999;

export function isUnlimited(n: number): boolean {
  return !n || n >= UNLIMITED;
}

// 是否為付費方案（free 以外皆算，含 lab）
export function hasPaidTier(tier: string): boolean {
  return (TIER_RANK[tier as TierCode] ?? 0) > 0;
}

export const TIER_DEFS: Record<TierCode, Record<string, number>> = {
  free: {
    daily_search_limit: 20, daily_deep_limit: 5, daily_litreview_limit: 3, daily_gap_analysis_limit: 3,
    daily_export_limit: 10, daily_digest_limit: 2, daily_chat_limit: 3, drive_monthly_limit: 20, follow_limit: 3, category_limit: 5,
  },
  basic: {
    daily_search_limit: 50, daily_deep_limit: 15, daily_litreview_limit: 10, daily_gap_analysis_limit: 10,
    daily_export_limit: 25, daily_digest_limit: 5, daily_chat_limit: 10, drive_monthly_limit: 50, follow_limit: 10, category_limit: 20,
  },
  standard: {
    daily_search_limit: 150, daily_deep_limit: 50, daily_litreview_limit: 25, daily_gap_analysis_limit: 25,
    daily_export_limit: 80, daily_digest_limit: 10, daily_chat_limit: 25, drive_monthly_limit: 100, follow_limit: 30, category_limit: UNLIMITED,
  },
  premium: {
    daily_search_limit: 300, daily_deep_limit: 150, daily_litreview_limit: 100, daily_gap_analysis_limit: 100,
    daily_export_limit: 250, daily_digest_limit: 20, daily_chat_limit: 100, drive_monthly_limit: UNLIMITED, follow_limit: UNLIMITED, category_limit: UNLIMITED,
  },
  ultra: {
    daily_search_limit: 500, daily_deep_limit: 300, daily_litreview_limit: UNLIMITED, daily_gap_analysis_limit: UNLIMITED,
    daily_export_limit: UNLIMITED, daily_digest_limit: 50, daily_chat_limit: UNLIMITED, drive_monthly_limit: UNLIMITED, follow_limit: UNLIMITED, category_limit: UNLIMITED,
  },
  lab: {
    daily_search_limit: UNLIMITED, daily_deep_limit: UNLIMITED, daily_litreview_limit: UNLIMITED, daily_gap_analysis_limit: UNLIMITED,
    daily_export_limit: UNLIMITED, daily_digest_limit: UNLIMITED, daily_chat_limit: UNLIMITED, drive_monthly_limit: UNLIMITED, follow_limit: UNLIMITED, category_limit: UNLIMITED,
  },
};

export const TIER_PRICES: Record<TierCode, number> = {
  free: 0, basic: 150, standard: 299, premium: 499, ultra: 999, lab: 2999,
};

export const TIER_RANK: Record<TierCode, number> = {
  free: 0, basic: 1, standard: 2, premium: 3, ultra: 4, lab: 5,
};

export const TIER_ORDER: TierCode[] = ['free', 'basic', 'standard', 'premium', 'ultra', 'lab'];

// 各等級的賣點（用於對比表下方簡述），key 對應 i18n 的 pro_tier_*_pitch
export const TIER_PITCH_KEY: Record<TierCode, string> = {
  free: 'pro_tier_free_pitch',
  basic: 'pro_tier_basic_pitch',
  standard: 'pro_tier_standard_pitch',
  premium: 'pro_tier_premium_pitch',
  ultra: 'pro_tier_ultra_pitch',
  lab: 'pro_tier_lab_pitch',
};
