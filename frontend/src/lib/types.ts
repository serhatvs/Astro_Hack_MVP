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
export type RiskLevel = "low" | "moderate" | "high";
export type MissionStatus = "NOMINAL" | "WATCH" | "CRITICAL";
export type ApiStatus = "idle" | "loading" | "ready" | "warning" | "error";

export interface DemoSelection {
  selected_crop: string;
  selected_algae: string;
  selected_microbial: string;
}

export interface DemoCase {
  name: string;
  description: string;
  expected_outcome: string;
  selected_stack?: DemoSelection | null;
  environment: Environment;
  duration: Duration;
  constraints: MissionConstraints;
  goal: BackendGoal;
}

export interface HealthResponse {
  status: string;
  service: string;
}

export interface AuthUser {
  id: string;
  email: string;
  created_at: string;
  is_active: boolean;
}

export interface AuthPayload {
  email: string;
  password: string;
}

export interface AuthResponse {
  user: AuthUser;
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

export interface WaterRecoveryEntry {
  week_used: number;
  amount_used: number;
  cycle_weeks: number;
  recovery_rate: number;
}

export interface MissionState {
  mission_id: string;
  environment: Environment;
  duration: Duration;
  goal: BackendGoal;
  constraints: MissionConstraints;
  time: number;
  max_weeks: number;
  initial_risk_level: number;
  end_reason?: string | null;
  resources: MissionStateResourceSet;
  water_recovery_queue: WaterRecoveryEntry[];
  last_consumed_water: number;
  last_recovered_water: number;
  water_recovery_cycle_weeks: number;
  water_recovery_rate: number;
  last_consumed_energy: number;
  last_solar_energy: number;
  last_photosynthesis_energy: number;
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

export interface RankedDomainCandidate {
  name: string;
  type: "crop" | "algae" | "microbial";
  rank: number;
  domain_score: number;
  mission_fit_score: number;
  risk_score: number;
  combined_score: number;
  support_system?: string | null;
  summary: string;
  notes: string[];
}

export interface RankedCandidatesBundle {
  crop: RankedDomainCandidate[];
  algae: RankedDomainCandidate[];
  microbial: RankedDomainCandidate[];
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

export interface UIEnhancedNarrative {
  crop_note: string;
  algae_note: string;
  microbial_note: string;
  executive_summary: string;
  adaptation_summary: string;
}

export interface RecommendationResponse {
  mission_profile: MissionPayload;
  mission_state?: MissionState;
  selected_system?: SelectedSystemBundle;
  ranked_candidates?: RankedCandidatesBundle;
  scores?: ScoreBundle;
  explanations?: ExplanationBundle;
  ui_enhanced?: UIEnhancedNarrative;
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

export interface SimulationStartPayload {
  mission_profile: MissionPayload;
  selected_crop: string;
  selected_algae: string;
  selected_microbial: string;
}

export interface SimulationStartResponse {
  mission_profile: MissionPayload;
  mission_state: MissionState;
  selected_system: SelectedSystemBundle;
  ranked_candidates: RankedCandidatesBundle;
  scores: ScoreBundle;
  explanations: ExplanationBundle;
  ui_enhanced: UIEnhancedNarrative;
  llm_analysis: LLMAnalysis;
  mission_status: MissionStatus;
  operational_note: string;
}

export interface MissionEventsPayload {
  water_drop?: number;
  energy_drop?: number;
  contamination?: number;
  yield_variation?: number;
}

export interface MissionStepPayload {
  mission_id: string;
  time_step: number;
  events?: MissionEventsPayload;
}

export interface MissionStepResponse {
  mission_state: MissionState;
  selected_system: SelectedSystemBundle;
  ranked_candidates: RankedCandidatesBundle;
  scores: ScoreBundle;
  explanations: ExplanationBundle;
  ui_enhanced: UIEnhancedNarrative;
  llm_analysis: LLMAnalysis;
  mission_status: MissionStatus;
  operational_note: string;
  system_changes: string[];
  risk_delta: number;
  adaptation_summary: string;
  events?: MissionEventsPayload | null;
  request: MissionStepPayload;
}

export interface TerminalEntry {
  level: "info" | "warn" | "success" | "error";
  text: string;
}
