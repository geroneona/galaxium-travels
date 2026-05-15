import { Dropdown } from '@carbon/react';
import { useTheme } from '../../hooks/useTheme';
import { themes } from '../../theme/carbonTheme';
import type { ThemeType } from '../../theme/carbonTheme';

export const ThemeSwitcher = () => {
  const { theme, setTheme } = useTheme();

  const themeOptions = Object.values(themes).map((t) => ({
    id: t.theme,
    label: t.label,
    description: t.description,
  }));

  const selectedItem = themeOptions.find((opt) => opt.id === theme);

  return (
    <div className="theme-switcher">
      <Dropdown
        id="theme-selector"
        titleText="Theme"
        label={selectedItem?.label || 'Select theme'}
        items={themeOptions}
        itemToString={(item) => (item ? item.label : '')}
        selectedItem={selectedItem}
        onChange={({ selectedItem }) => {
          if (selectedItem) {
            setTheme(selectedItem.id as ThemeType);
          }
        }}
      />
    </div>
  );
};

// Made with Bob