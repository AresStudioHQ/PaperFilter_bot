// 訂閱等級單一資料源：與 bot 端 database.py 的 TIER_DEFS / TIER_PRICES / TIER_RANK 完全一致。
// 商業化只保留 Free / Pro。舊的 basic/standard/premium/ultra/lab 讀取時一律視為 Pro。

export type TierCode = 'free' | 'pro';

export const UNLIMITED = 999999;

export function isUnlimited(n: number): boolean {
  return !n || n >= UNLIMITED;
}

/** 舊方案代碼對應到 Pro（資料庫可能仍存 premium / lab 等） */
export const LEGACY_PAID_TIERS = new Set([
  'basic', 'standard', 'premium', 'ultra', 'lab', 'pro',
]);

export function normalizeTier(tier: string | null | undefined): TierCode {
  if (!tier || tier === 'free') return 'free';
  if (LEGACY_PAID_TIERS.has(tier)) return 'pro';
  return 'free';
}

export function hasPaidTier(tier: string): boolean {
  return normalizeTier(tier) === 'pro';
}

export const TIER_DEFS: Record<TierCode, Record<string, number>> = {
  free: {
    daily_search_limit: 15,
    daily_deep_limit: 3,
    daily_litreview_limit: 1,
    daily_gap_analysis_limit: 1,
    daily_export_limit: 5,
    daily_digest_limit: 0,
    daily_chat_limit: 2,
    drive_monthly_limit: 10,
    follow_limit: 3,
    category_limit: 5,
    library_limit: 80,
  },
  pro: {
    daily_search_limit: 80,
    daily_deep_limit: 25,
    daily_litreview_limit: 10,
    daily_gap_analysis_limit: 10,
    daily_export_limit: 80,
    daily_digest_limit: 7,
    daily_chat_limit: 20,
    drive_monthly_limit: 200,
    follow_limit: 30,
    category_limit: UNLIMITED,
    library_limit: 2000,
  },
};

export const TIER_PRICES: Record<TierCode, number> = {
  free: 0,
  pro: 299,
};

export const TIER_RANK: Record<TierCode, number> = {
  free: 0,
  pro: 1,
};

export const TIER_ORDER: TierCode[] = ['free', 'pro'];

export const TIER_PITCH_KEY: Record<TierCode, string> = {
  free: 'pro_tier_free_pitch',
  pro: 'pro_tier_pro_pitch',
};
