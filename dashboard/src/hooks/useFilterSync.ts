import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useFilterStore } from '../store/filterStore';

export function useFilterSync() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { channelId, programId, videoId, startDate, endDate } = useFilterStore();

  // Read URL params on initial mount and write to store
  useEffect(() => {
    const urlChannel = searchParams.get('channel_id');
    const urlProgram = searchParams.get('program_id');
    const urlVideo = searchParams.get('video_id');
    const urlStart = searchParams.get('start_date');
    const urlEnd = searchParams.get('end_date');

    const store = useFilterStore.getState();
    if (urlChannel !== store.channelId) store.setChannel(urlChannel);
    if (urlProgram !== store.programId) store.setProgram(urlProgram);
    if (urlVideo !== store.videoId) store.setVideo(urlVideo);
    if (urlStart !== store.startDate || urlEnd !== store.endDate) {
      store.setDateRange(urlStart, urlEnd);
    }
  }, []);

  // Update URL search params whenever store filter state changes
  useEffect(() => {
    const params = new URLSearchParams(searchParams);

    if (channelId) params.set('channel_id', channelId);
    else params.delete('channel_id');

    if (programId) params.set('program_id', programId);
    else params.delete('program_id');

    if (videoId) params.set('video_id', videoId);
    else params.delete('video_id');

    if (startDate) params.set('start_date', startDate);
    else params.delete('start_date');

    if (endDate) params.set('end_date', endDate);
    else params.delete('end_date');

    if (params.toString() !== searchParams.toString()) {
      setSearchParams(params, { replace: true });
    }
  }, [channelId, programId, videoId, startDate, endDate]);
}
