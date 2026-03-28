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
export type MissionStatus = "NOMINAL" | "WATCH" | "CRITICAL";
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

export interface MissionStateResourceSet {
  water: number;
  energy: number;
  area: number;
}

export interface MissionStateMetrics {
  oxygen_level: number;
  co2_balance: number;
  food_supply: number;
  nutrient_cycle_efficiency: number;
  risk_level: number;
}

export interface MissionStateActiveItem {
  name: string;
  type: "crop" | "algae" | "microbial";
  score: number;
  support_system?: string | null;
}

export interface MissionState {
  mission_id: string;
  environment: Environment;
  duration: Duration;
  goal: BackendGoal;
  time: number;
  resources: MissionStateResourceSet;
  active_system: {
    crops: MissionStateActiveItem[];
    algae: MissionStateActiveItem[];
    microbial: MissionStateActiveItem[];
  };
  system_metrics: MissionStateMetrics;
  history: Array<{
    time: number;
    event: string;
    summary: string;
    selected_crop?: string | null;
    selected_algae?: string | null;
    selected_microbial?: string | null;
    risk_level: number;
  }>;
}

export interface SelectedDomainSystem {
  name: string;
  type: "crop" | "algae" | "microbial";
  domain_score: number;
  mission_fit_score: number;
  risk_score: number;
  support_system?: string | null;
  metrics: Record<string, number>;
  notes: string[];
}

export interface SelectedSystemBundle {
  crop: SelectedDomainSystem;
  algae: SelectedDomainSystem;
  microbial: SelectedDomainSystem;
}

export interface ScoreBundle {
  domain: {
    crop: {
      domain_score: number;
      mission_fit_score: number;
      risk_score: number;
    };
    algae: {
      domain_score: number;
      mission_fit_score: number;
      risk_score: number;
    };
    microbial: {
      domain_score: number;
      mission_fit_score: number;
      risk_score: number;
    };
  };
  interaction: {
    synergy_score: number;
    conflict_score: number;
    complexity_penalty: number;
    resource_overlap: number;
    loop_closure_bonus: number;
  };
  integrated: number;
}

export interface ExplanationBundle {
  executive_summary: string;
  system_reasoning: string;
  tradeoffs: string;
  weak_points: string;
}

export interface LLMAnalysis {
  reasoning_summary: string;
  weaknesses: string[];
  improvements: string[];
  improvement_suggestions: string[];
  alternative: Record<string, unknown>;
  alternative_configuration: Record<string, unknown>;
  second_pass: Record<string, unknown>;
  second_pass_decision: Record<string, unknown>;
}

export interface RecommendationResponse {
  mission_profile: MissionPayload;
  mission_state?: MissionState;
  selected_system?: SelectedSystemBundle;
  scores?: ScoreBundle;
  explanations?: ExplanationBundle;
  llm_analysis?: LLMAnalysis;
  top_crops: CropRecommendation[];
  recommended_system: string;
  system_reason: string;
  system_reasoning: string;
  why_this_system: string;
  tradeoff_summary: string;
  resource_plan: ResourcePlan;
  risk_analysis: RiskAnalysis;
  mission_status: MissionStatus;
  executive_summary: string;
  operational_note: string;
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
  risk_score_delta: number;
  previous_mission_status: MissionStatus;
  new_mission_status: MissionStatus;
  updated_mission_profile: MissionPayload;
  updated_recommendation: RecommendationResponse;
  adaptation_summary: string;
  reason: string;
  adaptation_reason: string;
}

export interface TerminalEntry {
  level: "info" | "warn" | "success" | "error";
  text: string;
}
