export type Environment = "mars" | "moon" | "iss";
export type Duration = "short" | "medium" | "long";
export type ConstraintLevel = "low" | "medium" | "high";
export type BackendGoal =
  | "balanced"
  | "calorie_max"
  | "water_efficiency"
  | "low_maintenance";
export type UiGoal = "balanced" | "calorie" | "water" | "low_maintenance";
export type CrisisType = "water" | "energy" | "yield";
export type ChangeEvent = "water_drop" | "energy_drop" | "yield_drop";
export type RiskLevel = "low" | "moderate" | "high";
export type RiskDelta = "increased" | "decreased" | "unchanged";
export type ApiStatus = "idle" | "loading" | "ready" | "warning" | "error";

export interface DemoCase {
  name: string;
  environment: Environment;
  duration: Duration;
  constraints: MissionConstraints;
  goal: BackendGoal;
}

export interface HealthResponse {
  status: string;
  service: string;
}

export interface MissionConstraints {
  water: ConstraintLevel;
  energy: ConstraintLevel;
  area: ConstraintLevel;
}

export interface MissionPayload {
  environment: Environment;
  duration: Duration;
  constraints: MissionConstraints;
  goal: BackendGoal;
}

export interface MetricBreakdown {
  calorie: number;
  water: number;
  energy: number;
  growth_time: number;
  risk: number;
  maintenance: number;
}

export interface CropRecommendation {
  name: string;
  score: number;
  reason: string;
  selected_system: string;
  strengths: string[];
  tradeoffs: string[];
  metric_breakdown: MetricBreakdown;
  compatibility_score: number;
}

export interface ResourcePlan {
  water_level: string;
  energy_level: string;
  area_usage: string;
  water_score: number;
  energy_score: number;
  area_score: number;
  maintenance_score: number;
  calorie_score: number;
}

export interface RiskAnalysis {
  level: RiskLevel;
  score: number;
  factors: string[];
}

export interface RecommendationResponse {
  mission_profile: MissionPayload;
  top_crops: CropRecommendation[];
  recommended_system: string;
  system_reason: string;
  resource_plan: ResourcePlan;
  risk_analysis: RiskAnalysis;
  explanation: string;
}

export interface SimulationPayload {
  mission_profile: MissionPayload;
  change_event: ChangeEvent;
  affected_crop?: string;
  previous_recommendation?: RecommendationResponse;
}

export interface SimulationResponse {
  change_event: ChangeEvent;
  changed_fields: string[];
  previous_top_crop: string | null;
  new_top_crop: string | null;
  ranking_diff: Record<string, number>;
  system_changed: boolean;
  previous_system: string | null;
  new_system: string | null;
  risk_delta: RiskDelta;
  updated_mission_profile: MissionPayload;
  updated_recommendation: RecommendationResponse;
  reason: string;
  adaptation_reason: string;
}

export interface TerminalEntry {
  level: "info" | "warn" | "success" | "error";
  text: string;
}
