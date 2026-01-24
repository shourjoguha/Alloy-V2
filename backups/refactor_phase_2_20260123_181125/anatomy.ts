export type MuscleGroup =
  | 'Quadriceps'
  | 'Hamstrings'
  | 'Glutes'
  | 'Calves'
  | 'Chest'
  | 'Lats'
  | 'Upper Back'
  | 'Rear Delts'
  | 'Front Delts'
  | 'Side Delts'
  | 'Biceps'
  | 'Triceps'
  | 'Forearms'
  | 'Core'
  | 'Obliques'
  | 'Lower Back'
  | 'Hip Flexors'
  | 'Adductors';

export type BodyZone =
  | 'posterior_upper'
  | 'anterior_upper'
  | 'full_body'
  | 'shoulder'
  | 'core'
  | 'posterior_lower'
  | 'anterior_lower';

export const ZONE_MAPPING: Record<BodyZone, MuscleGroup[]> = {
  posterior_upper: ['Upper Back', 'Lats', 'Rear Delts'],
  anterior_upper: ['Chest', 'Front Delts', 'Biceps'],
  shoulder: ['Front Delts', 'Side Delts', 'Rear Delts'],
  core: ['Core', 'Obliques', 'Lower Back'],
  posterior_lower: ['Hamstrings', 'Glutes', 'Calves'],
  anterior_lower: ['Quadriceps', 'Hip Flexors', 'Adductors'],
  full_body: [
    'Quadriceps',
    'Hamstrings',
    'Glutes',
    'Calves',
    'Chest',
    'Lats',
    'Upper Back',
    'Rear Delts',
    'Front Delts',
    'Side Delts',
    'Biceps',
    'Triceps',
    'Forearms',
    'Core',
    'Obliques',
    'Lower Back',
    'Hip Flexors',
    'Adductors',
  ],
};

export const BODY_ZONE_LABELS: Record<BodyZone, string> = {
  posterior_upper: 'Posterior Upper',
  anterior_upper: 'Anterior Upper',
  full_body: 'Full Body',
  shoulder: 'Shoulder',
  core: 'Core',
  posterior_lower: 'Posterior Lower',
  anterior_lower: 'Anterior Lower',
};

export const MUSCLE_DISPLAY_NAMES: Record<MuscleGroup, string> = {
  Quadriceps: 'Quadriceps',
  Hamstrings: 'Hamstrings',
  Glutes: 'Glutes',
  Calves: 'Calves',
  Chest: 'Chest',
  Lats: 'Lats',
  'Upper Back': 'Upper Back',
  'Rear Delts': 'Rear Delts',
  'Front Delts': 'Front Delts',
  'Side Delts': 'Side Delts',
  Biceps: 'Biceps',
  Triceps: 'Triceps',
  Forearms: 'Forearms',
  Core: 'Core',
  Obliques: 'Obliques',
  'Lower Back': 'Lower Back',
  'Hip Flexors': 'Hip Flexors',
  Adductors: 'Adductors',
};
