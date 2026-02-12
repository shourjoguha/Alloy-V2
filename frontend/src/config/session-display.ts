import type { SessionType } from '@/types';
import { GenerationStatus } from '@/types';

export interface SessionDisplayConfig {
  label: string;
  icon: string;
  color: string;
}

export interface GenerationStatusConfig {
  label: string;
  color: string;
  bg: string;
}

export const SESSION_TYPE_CONFIG: Record<SessionType, SessionDisplayConfig> = {
  upper: { label: "Upper Body", icon: "💪", color: "bg-blue-500" },
  lower: { label: "Lower Body", icon: "🦵", color: "bg-green-500" },
  push: { label: "Push", icon: "🏋️", color: "bg-red-500" },
  pull: { label: "Pull", icon: "🧲", color: "bg-purple-500" },
  legs: { label: "Legs", icon: "🦵", color: "bg-green-500" },
  full_body: { label: "Full Body", icon: "⚡", color: "bg-yellow-500" },
  cardio: { label: "Cardio", icon: "❤️", color: "bg-pink-500" },
  mobility: { label: "Mobility", icon: "🧘", color: "bg-teal-500" },
  recovery: { label: "Rest Day", icon: "😴", color: "bg-gray-500" },
  skill: { label: "Skill", icon: "🎯", color: "bg-orange-500" },
  custom: { label: "Custom", icon: "⚙️", color: "bg-gray-500" },
};

export const GENERATION_STATUS_CONFIG: Record<GenerationStatus, GenerationStatusConfig> = {
  [GenerationStatus.PENDING]: { label: "Pending", color: "text-gray-400", bg: "bg-gray-500/10" },
  [GenerationStatus.IN_PROGRESS]: { label: "Generating", color: "text-primary", bg: "bg-primary/10" },
  [GenerationStatus.COMPLETED]: { label: "Generated", color: "text-success", bg: "bg-success/10" },
  [GenerationStatus.FAILED]: { label: "Failed", color: "text-destructive", bg: "bg-destructive/10" },
  [GenerationStatus.ESTIMATED]: { label: "Estimated", color: "text-blue-400", bg: "bg-blue-500/10" },
};
