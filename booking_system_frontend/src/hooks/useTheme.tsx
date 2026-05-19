import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { defaultTheme } from '../theme/carbonTheme';
import type { ThemeType } from '../theme/carbonTheme';

interface ThemeContextType {
  theme: ThemeType;
  setTheme: (theme: ThemeType) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider = ({ children }: { children: ReactNode }) => {
  const [theme, setThemeState] = useState<ThemeType>(() => {
    // Load theme from localStorage or use default
    const savedTheme = localStorage.getItem('carbon-theme') as ThemeType;
    return savedTheme || defaultTheme;
  });

  useEffect(() => {
    // Apply theme to document element
    document.documentElement.setAttribute('data-carbon-theme', theme);
    // Save to localStorage
    localStorage.setItem('carbon-theme', theme);
  }, [theme]);

  const setTheme = (newTheme: ThemeType) => {
    setThemeState(newTheme);
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

// Made with Bob