// IBM Carbon Design Theme Configuration
export type ThemeType = 'white' | 'g10' | 'g90' | 'g100';

export interface ThemeConfig {
  theme: ThemeType;
  label: string;
  description: string;
}

export const themes: Record<ThemeType, ThemeConfig> = {
  white: {
    theme: 'white',
    label: 'White',
    description: 'Light theme with white background'
  },
  g10: {
    theme: 'g10',
    label: 'Gray 10',
    description: 'Light theme with subtle gray background'
  },
  g90: {
    theme: 'g90',
    label: 'Gray 90',
    description: 'Dark theme with deep gray background'
  },
  g100: {
    theme: 'g100',
    label: 'Gray 100',
    description: 'Darkest theme with black background'
  }
};

export const defaultTheme: ThemeType = 'g90';

// Made with Bob