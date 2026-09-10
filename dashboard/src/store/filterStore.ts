import { create } from 'zustand';

export interface GlobalFilterState {
  channelId: string | null;
  programId: string | null;
  videoId: string | null;
  startDate: string | null;
  endDate: string | null;

  setChannel: (channelId: string | null) => void;
  setProgram: (programId: string | null, channelId?: string | null) => void;
  setVideo: (videoId: string | null) => void;
  setDateRange: (startDate: string | null, endDate: string | null) => void;
  clearAll: () => void;
}

export const useFilterStore = create<GlobalFilterState>((set) => ({
  channelId: null,
  programId: null,
  videoId: null,
  startDate: null,
  endDate: null,

  setChannel: (channelId) =>
    set({ channelId, programId: null, videoId: null }),

  setProgram: (programId, channelId) =>
    set((state) => ({
      programId,
      videoId: null,
      channelId: channelId !== undefined ? channelId : state.channelId,
    })),

  setVideo: (videoId) =>
    set({ videoId }),

  setDateRange: (startDate, endDate) =>
    set({ startDate, endDate }),

  clearAll: () =>
    set({
      channelId: null,
      programId: null,
      videoId: null,
      startDate: null,
      endDate: null,
    }),
}));
