export const NO_DATA = 255

export const RISK_LEVELS = [
  { label: 'Low', hex: '#eda26f', rgb: [237, 162, 111], heatAlpha: 60 },
  { label: 'Moderate', hex: '#dd7a33', rgb: [221, 122, 51], heatAlpha: 150 },
  { label: 'High', hex: '#c04f1d', rgb: [192, 79, 29], heatAlpha: 190 },
  { label: 'Severe', hex: '#8e2a16', rgb: [142, 42, 22], heatAlpha: 220 },
  { label: 'No Travel', hex: '#470e13', rgb: [71, 14, 19], heatAlpha: 240 },
] as const
