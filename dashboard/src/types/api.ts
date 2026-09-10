/**
 * API Response Interfaces for Public Pulse (Phase 11 + Phase 12B).
 * Strictly mirrors FastAPI Pydantic response schemas.
 */

export interface OverviewKPIOut {
  total_comments: number;
  valid_comments: number;
  noise_comments: number;
  pending_comments: number;
  noise_rate: number;
  total_videos: number;
  total_programs: number;
  total_channels: number;
  avg_comments_per_video: number;
}

export interface TopicDistributionItem {
  topic: string;
  count: number;
  percentage: number;
}

export interface TopicDistributionOut {
  program_id?: string | null;
  channel_id?: string | null;
  video_id?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  total_valid_comments: number;
  distribution: TopicDistributionItem[];
}

export interface StanceDistributionItem {
  stance: string;
  count: number;
  percentage: number;
}

export interface StanceDistributionOut {
  program_id?: string | null;
  channel_id?: string | null;
  video_id?: string | null;
  topic_filter?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  total_valid_comments: number;
  distribution: StanceDistributionItem[];
}

export interface TopicStanceMatrixOut {
  program_id?: string | null;
  channel_id?: string | null;
  video_id?: string | null;
  matrix: Record<string, Record<string, number>>;
}

export interface EntityMatrixOut {
  entity_type: 'program' | 'channel';
  matrix_type: 'topic' | 'stance';
  matrix: Record<string, Record<string, number>>;
}

export interface VolumeDataPoint {
  date: string;
  total_comments: number;
  valid_comments: number;
  noise_comments: number;
}

export interface VolumeOverTimeOut {
  program_id?: string | null;
  channel_id?: string | null;
  video_id?: string | null;
  granularity: 'daily' | 'weekly' | 'monthly';
  data_points: VolumeDataPoint[];
}

export interface PeriodOverPeriodOut {
  period_days: number;
  current_period: {
    start_date?: string;
    end_date?: string;
    metrics?: OverviewKPIOut;
  };
  previous_period: {
    start_date?: string;
    end_date?: string;
    metrics?: OverviewKPIOut;
  };
  changes: {
    volume_change_pct?: number;
    noise_rate_change?: number;
  };
}

export interface VideoAnalyticsItem {
  video_id: string;
  title?: string | null;
  program_name: string;
  published_at?: string | null;
  total_comments: number;
  valid_comments: number;
  noise_rate: number;
  top_topic?: string | null;
  stance_breakdown: Record<string, number>;
}

export interface VideoAnalyticsOut {
  items: VideoAnalyticsItem[];
  total: number;
}

export interface DataQualityAnalyticsOut {
  overview: OverviewKPIOut;
  average_confidence_by_layer: Record<string, number>;
  subissue_status: string;
}

export interface FaithfulnessAnalyticsOut {
  total_verifications: number;
  mean_grounding_score: number;
  mean_claim_support_rate: number;
  mean_partial_support_rate: number;
  mean_unsupported_claim_rate: number;
  mean_contradiction_rate: number;
  mean_citation_precision: number;
}

export interface ChannelOut {
  id: string;
  name: string;
  channel_url?: string | null;
  description?: string | null;
  subscriber_count?: number | null;
  created_at: string;
}

export interface ProgramOut {
  id: string;
  channel_id: string;
  channel_name: string;
  name: string;
  platform: string;
  is_active: boolean;
  created_at: string;
}

export interface VideoOut {
  id: string;
  program_id: string;
  title?: string | null;
  published_at?: string | null;
  duration_seconds?: number | null;
  is_live: boolean;
  comment_count?: number | null;
  scraped_at: string;
}

export interface EvidenceRetrievalIn {
  top_k?: number;
  topic?: string | null;
  stance?: string;
  program_id?: string | null;
  channel_id?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  keywords?: string[];
}

export interface EvidenceItemOut {
  rank: number;
  evidence_id: string;
  comment_id: string;
  text_clean: string;
  posted_at?: string | null;
  video_id: string;
  video_title?: string | null;
  program_name: string;
  channel_name: string;
  layer2_topic: string;
  layer2_confidence: number;
  layer4_stance: string;
  layer4_confidence: number;
  like_count: number;
  relevance_score: number;
}

export interface EvidencePayloadOut {
  evidence_set_id: string;
  retrieved_at: string;
  evidence_count: number;
  total_matching_count: number;
  retrieval_method: string;
  evidence_items: EvidenceItemOut[];
}

export interface FindingOut {
  finding_id: string;
  text: string;
  evidence_ids: string[];
  confidence: string;
}

export interface InsightOut {
  insight_id: string;
  evidence_set_id?: string | null;
  program_id?: string | null;
  query?: string | null;
  insight_type: string;
  generation_status: string;
  summary?: string | null;
  findings: FindingOut[];
  discourse_interpretation?: string | null;
  limitations?: string | null;
  uncertainty_note?: string | null;
  llm_provider: string;
  llm_model: string;
  prompt_version: string;
  generated_at: string;
  evidence_count_used: number;
  stance_distribution?: Record<string, number> | null;
  error_message?: string | null;
}

export interface JobStatusOut {
  job_id: string;
  job_type: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  reference_id?: string | null;
  error?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface ClaimVerificationOut {
  claim_id: string;
  finding_id: string;
  claim_text: string;
  label: 'SUPPORTED' | 'PARTIALLY_SUPPORTED' | 'UNSUPPORTED' | 'CONTRADICTED';
  evidence_ids: string[];
  verification_method: string;
  reason: string;
}

export interface VerificationReportOut {
  verification_id: string;
  insight_id: string;
  evidence_set_id: string;
  claim_support_rate: number;
  partial_support_rate: number;
  unsupported_claim_rate: number;
  contradiction_rate: number;
  grounding_score: number;
  evidence_citation_precision: number;
  total_claims_evaluated: number;
  claim_verifications: ClaimVerificationOut[];
  verifier_method: string;
  verifier_model?: string | null;
  verified_at: string;
}
