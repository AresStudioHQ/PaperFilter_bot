// Loads tier credibility-badge translations from src/_i18n_tier.json into the
// shared TRANSLATIONS dictionary so that useI18n's t() can resolve tier_* keys.
// This module only mutates the runtime dictionary; it does NOT edit i18n.ts.
import { TRANSLATIONS } from './i18n';
import tierTranslations from './_i18n_tier.json';
import type { Language } from './i18n';

const LANGS: Language[] = ['zh_hant', 'zh_hans', 'en', 'ja'];
const dict = tierTranslations as Record<string, Partial<Record<Language, string>>>;

for (const lang of LANGS) {
  for (const [key, langs] of Object.entries(dict)) {
    if (langs[lang]) {
      TRANSLATIONS[lang][key] = langs[lang] as string;
    }
  }
}

export {};
