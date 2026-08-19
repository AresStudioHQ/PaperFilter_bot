export interface AIModel {
  id: string;
  name: string;
  required_tier: string;
  unlocked: boolean;
}

const KEY = 'pf_selected_model';

let current: string =
  typeof localStorage !== 'undefined' ? localStorage.getItem(KEY) || '' : '';

export function getModel(): string {
  return current;
}

export function setModel(m: string): void {
  current = m;
  if (typeof localStorage !== 'undefined') localStorage.setItem(KEY, m);
}
