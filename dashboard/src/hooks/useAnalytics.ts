import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { useFilterStore } from '../store/filterStore';

export function useGlobalFilters() {
  const { channelId, programId, videoId, startDate, endDate } = useFilterStore();
  return { channel_id: channelId, program_id: programId, video_id: videoId, start_date: startDate, end_date: endDate };
}

export function useOverviewKPIs(overrideParams?: Record<string, any>) {
  const filters = useGlobalFilters();
  const params = { ...filters, ...overrideParams };
  return useQuery({
    queryKey: ['analytics', 'overview', params],
    queryFn: () => api.getOverview(params),
    staleTime: 5 * 60 * 1000,
  });
}

export function useTopicDistribution(overrideParams?: Record<string, any>) {
  const filters = useGlobalFilters();
  const params = { ...filters, ...overrideParams };
  return useQuery({
    queryKey: ['analytics', 'topics', params],
    queryFn: () => api.getTopics(params),
    staleTime: 5 * 60 * 1000,
  });
}

export function useStanceDistribution(topicFilter?: string | null, overrideParams?: Record<string, any>) {
  const filters = useGlobalFilters();
  const params = { ...filters, topic_filter: topicFilter, ...overrideParams };
  return useQuery({
    queryKey: ['analytics', 'stances', params],
    queryFn: () => api.getStances(params),
    staleTime: 5 * 60 * 1000,
  });
}

export function useTopicStanceMatrix(overrideParams?: Record<string, any>) {
  const filters = useGlobalFilters();
  const params = { ...filters, ...overrideParams };
  return useQuery({
    queryKey: ['analytics', 'topic-stance-matrix', params],
    queryFn: () => api.getTopicStanceMatrix(params),
    staleTime: 5 * 60 * 1000,
  });
}

export function useEntityMatrix(entityType: 'program' | 'channel', matrixType: 'topic' | 'stance') {
  const { channel_id, start_date, end_date } = useGlobalFilters();
  return useQuery({
    queryKey: ['analytics', 'entity-matrix', entityType, matrixType, channel_id, start_date, end_date],
    queryFn: () => api.getEntityMatrix({ entity_type: entityType, matrix_type: matrixType, channel_id, start_date, end_date }),
    staleTime: 5 * 60 * 1000,
  });
}

export function useVolumeOverTime(granularity: 'daily' | 'weekly' | 'monthly' = 'daily', overrideParams?: Record<string, any>) {
  const filters = useGlobalFilters();
  const params = { ...filters, granularity, ...overrideParams };
  return useQuery({
    queryKey: ['analytics', 'volume-over-time', params],
    queryFn: () => api.getVolumeOverTime(params),
    staleTime: 5 * 60 * 1000,
  });
}

export function usePeriodOverPeriod(periodDays: number = 30) {
  const { channel_id, program_id } = useGlobalFilters();
  return useQuery({
    queryKey: ['analytics', 'period-over-period', periodDays, channel_id, program_id],
    queryFn: () => api.getPeriodOverPeriod({ period_days: periodDays, channel_id, program_id }),
    staleTime: 5 * 60 * 1000,
  });
}

export function useEpisodes(limit = 20, offset = 0) {
  const { channel_id, program_id } = useGlobalFilters();
  return useQuery({
    queryKey: ['analytics', 'episodes', limit, offset, channel_id, program_id],
    queryFn: () => api.getEpisodes({ limit, offset, channel_id, program_id }),
    staleTime: 5 * 60 * 1000,
  });
}

export function useDataQuality() {
  const { channel_id, program_id, start_date, end_date } = useGlobalFilters();
  return useQuery({
    queryKey: ['analytics', 'data-quality', channel_id, program_id, start_date, end_date],
    queryFn: () => api.getDataQuality({ channel_id, program_id, start_date, end_date }),
    staleTime: 5 * 60 * 1000,
  });
}

export function useFaithfulnessAnalytics() {
  const { program_id } = useGlobalFilters();
  return useQuery({
    queryKey: ['analytics', 'faithfulness', program_id],
    queryFn: () => api.getFaithfulness({ program_id }),
    staleTime: 5 * 60 * 1000,
  });
}

export function useChannels() {
  return useQuery({
    queryKey: ['channels'],
    queryFn: () => api.getChannels(),
    staleTime: 30 * 60 * 1000,
  });
}

export function usePrograms(channelId?: string | null) {
  return useQuery({
    queryKey: ['programs', channelId],
    queryFn: () => api.getPrograms({ channel_id: channelId }),
    staleTime: 30 * 60 * 1000,
  });
}

export function useProgramDetail(programId?: string | null) {
  return useQuery({
    queryKey: ['program', programId],
    queryFn: () => {
      if (!programId) throw new Error('No programId');
      return api.getProgram(programId);
    },
    enabled: Boolean(programId),
  });
}

export function useInsights(programId?: string | null) {
  return useQuery({
    queryKey: ['insights', programId],
    queryFn: () => api.listInsights({ program_id: programId }),
    staleTime: 2 * 60 * 1000,
  });
}

export function useInsightDetail(insightId?: string | null) {
  return useQuery({
    queryKey: ['insight', insightId],
    queryFn: () => {
      if (!insightId) throw new Error('No insightId');
      return api.getInsight(insightId);
    },
    enabled: Boolean(insightId),
  });
}

export function useVerificationReport(insightId?: string | null) {
  return useQuery({
    queryKey: ['verification', insightId],
    queryFn: () => {
      if (!insightId) throw new Error('No insightId');
      return api.getVerificationReport(insightId);
    },
    enabled: Boolean(insightId),
    retry: false,
  });
}
