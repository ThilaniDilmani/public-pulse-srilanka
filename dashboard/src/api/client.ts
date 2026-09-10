import axios from 'axios';
import type {
  ChannelOut,
  ProgramOut,
  VideoOut,
  OverviewKPIOut,
  TopicDistributionOut,
  StanceDistributionOut,
  TopicStanceMatrixOut,
  EntityMatrixOut,
  VolumeOverTimeOut,
  PeriodOverPeriodOut,
  VideoAnalyticsOut,
  DataQualityAnalyticsOut,
  FaithfulnessAnalyticsOut,
  EvidenceRetrievalIn,
  EvidencePayloadOut,
  InsightOut,
  JobStatusOut,
  VerificationReportOut,
} from '../types/api';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
const API_KEY = import.meta.env.VITE_API_KEY || '';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
  },
});

// Helper to filter out null/undefined query parameters
function cleanParams(params: Record<string, any>) {
  const cleaned: Record<string, any> = {};
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== '') {
      cleaned[key] = value;
    }
  }
  return cleaned;
}

export const api = {
  // Health
  getHealth: () => apiClient.get('/health').then((r) => r.data),

  // Catalog
  getChannels: (): Promise<ChannelOut[]> =>
    apiClient.get('/channels').then((r) => r.data),

  getChannel: (channelId: string): Promise<ChannelOut> =>
    apiClient.get(`/channels/${channelId}`).then((r) => r.data),

  getChannelPrograms: (channelId: string): Promise<ProgramOut[]> =>
    apiClient.get(`/channels/${channelId}/programs`).then((r) => r.data),

  getPrograms: (params?: { channel_id?: string | null; is_active?: boolean | null }): Promise<ProgramOut[]> =>
    apiClient.get('/programs', { params: cleanParams(params || {}) }).then((r) => r.data),

  getProgram: (programId: string): Promise<ProgramOut> =>
    apiClient.get(`/programs/${programId}`).then((r) => r.data),

  getProgramVideos: (programId: string, params?: { limit?: number; offset?: number }): Promise<VideoOut[]> =>
    apiClient.get(`/programs/${programId}/videos`, { params: cleanParams(params || {}) }).then((r) => r.data),

  // Analytics
  getOverview: (params?: {
    program_id?: string | null;
    channel_id?: string | null;
    video_id?: string | null;
    start_date?: string | null;
    end_date?: string | null;
  }): Promise<OverviewKPIOut> =>
    apiClient.get('/analytics/overview', { params: cleanParams(params || {}) }).then((r) => r.data),

  getTopics: (params?: {
    program_id?: string | null;
    channel_id?: string | null;
    video_id?: string | null;
    start_date?: string | null;
    end_date?: string | null;
  }): Promise<TopicDistributionOut> =>
    apiClient.get('/analytics/topics', { params: cleanParams(params || {}) }).then((r) => r.data),

  getStances: (params?: {
    program_id?: string | null;
    channel_id?: string | null;
    video_id?: string | null;
    topic_filter?: string | null;
    start_date?: string | null;
    end_date?: string | null;
  }): Promise<StanceDistributionOut> =>
    apiClient.get('/analytics/stances', { params: cleanParams(params || {}) }).then((r) => r.data),

  getTopicStanceMatrix: (params?: {
    program_id?: string | null;
    channel_id?: string | null;
    video_id?: string | null;
    start_date?: string | null;
    end_date?: string | null;
  }): Promise<TopicStanceMatrixOut> =>
    apiClient.get('/analytics/topic-stance-matrix', { params: cleanParams(params || {}) }).then((r) => r.data),

  getEntityMatrix: (params: {
    entity_type?: 'program' | 'channel';
    matrix_type?: 'topic' | 'stance';
    channel_id?: string | null;
    start_date?: string | null;
    end_date?: string | null;
  }): Promise<EntityMatrixOut> =>
    apiClient.get('/analytics/entity-matrix', { params: cleanParams(params) }).then((r) => r.data),

  getVolumeOverTime: (params?: {
    program_id?: string | null;
    channel_id?: string | null;
    video_id?: string | null;
    granularity?: 'daily' | 'weekly' | 'monthly';
    start_date?: string | null;
    end_date?: string | null;
  }): Promise<VolumeOverTimeOut> =>
    apiClient.get('/analytics/volume-over-time', { params: cleanParams(params || {}) }).then((r) => r.data),

  getPeriodOverPeriod: (params?: {
    program_id?: string | null;
    channel_id?: string | null;
    period_days?: number;
  }): Promise<PeriodOverPeriodOut> =>
    apiClient.get('/analytics/period-over-period', { params: cleanParams(params || {}) }).then((r) => r.data),

  getEpisodes: (params?: {
    program_id?: string | null;
    channel_id?: string | null;
    limit?: number;
    offset?: number;
  }): Promise<VideoAnalyticsOut> =>
    apiClient.get('/analytics/episodes', { params: cleanParams(params || {}) }).then((r) => r.data),

  getDataQuality: (params?: {
    program_id?: string | null;
    channel_id?: string | null;
    start_date?: string | null;
    end_date?: string | null;
  }): Promise<DataQualityAnalyticsOut> =>
    apiClient.get('/analytics/data-quality', { params: cleanParams(params || {}) }).then((r) => r.data),

  getFaithfulness: (params?: {
    insight_id?: string | null;
    program_id?: string | null;
  }): Promise<FaithfulnessAnalyticsOut> =>
    apiClient.get('/analytics/faithfulness', { params: cleanParams(params || {}) }).then((r) => r.data),

  // Evidence
  retrieveEvidence: (body: EvidenceRetrievalIn): Promise<EvidencePayloadOut> =>
    apiClient.post('/evidence/retrieve', body).then((r) => r.data),

  // Insights
  listInsights: (params?: {
    program_id?: string | null;
    generation_status?: string | null;
    limit?: number;
    offset?: number;
  }): Promise<InsightOut[]> =>
    apiClient.get('/insights', { params: cleanParams(params || {}) }).then((r) => r.data),

  getInsight: (insightId: string): Promise<InsightOut> =>
    apiClient.get(`/insights/${insightId}`).then((r) => r.data),

  generateInsight: (body: { evidence_set_id: string; program_id?: string | null }): Promise<JobStatusOut> =>
    apiClient.post('/insights/generate', body).then((r) => r.data),

  // Verification
  verifyInsight: (insightId: string): Promise<JobStatusOut> =>
    apiClient.post(`/insights/${insightId}/verify`).then((r) => r.data),

  getVerificationReport: (insightId: string): Promise<VerificationReportOut> =>
    apiClient.get(`/insights/${insightId}/verification`).then((r) => r.data),

  // Jobs
  getJobStatus: (jobId: string): Promise<JobStatusOut> =>
    apiClient.get(`/jobs/${jobId}`).then((r) => r.data),
};
