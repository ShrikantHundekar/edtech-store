export interface PromoBanner {
  id: number;
  title: string;
  badge_text: string;
  description: string;
  academic_class?: number | null;
  class_name?: string;
  board_name?: string;
  monthly_pass_text: string;
  annual_pass_text: string;
  monthly_pass_url?: string | null;
  annual_pass_url?: string | null;
  gradient_theme: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PromoBannerInput {
  title: string;
  badge_text?: string;
  description: string;
  academic_class?: number | null;
  monthly_pass_text?: string;
  annual_pass_text?: string;
  monthly_pass_url?: string | null;
  annual_pass_url?: string | null;
  gradient_theme?: string;
  is_active?: boolean;
}
