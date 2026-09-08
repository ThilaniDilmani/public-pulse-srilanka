"""Analytics service wrapping repository functions for server-side aggregation (Phase 11)."""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from public_pulse.database import repository
from api.schemas.analytics import (
    DataQualityAnalyticsOut,
    EntityMatrixOut,
    FaithfulnessAnalyticsOut,
    OverviewKPIOut,
    PeriodOverPeriodOut,
    StanceDistributionItem,
    StanceDistributionOut,
    TopicDistributionItem,
    TopicDistributionOut,
    TopicStanceMatrixOut,
    VideoAnalyticsItem,
    VideoAnalyticsOut,
    VolumeDataPoint,
    VolumeOverTimeOut,
)


class AnalyticsService:

    @staticmethod
    def get_overview_kpis(
        db: Session,
        program_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        video_id: Optional[str] = None,
        start_date=None,
        end_date=None,
    ) -> OverviewKPIOut:
        data = repository.get_analytics_overview(
            db,
            program_id=program_id,
            channel_id=channel_id,
            video_id=video_id,
            start_date=start_date,
            end_date=end_date,
        )
        return OverviewKPIOut(**data)

    @staticmethod
    def get_topic_distribution(
        db: Session,
        program_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        video_id: Optional[str] = None,
        start_date=None,
        end_date=None,
    ) -> TopicDistributionOut:
        items = repository.get_topic_distribution(
            db,
            program_id=program_id,
            channel_id=channel_id,
            video_id=video_id,
            start_date=start_date,
            end_date=end_date,
        )
        total_valid = sum(i["count"] for i in items)
        return TopicDistributionOut(
            program_id=program_id,
            channel_id=channel_id,
            video_id=video_id,
            start_date=start_date,
            end_date=end_date,
            total_valid_comments=total_valid,
            distribution=[TopicDistributionItem(**i) for i in items],
        )

    @staticmethod
    def get_stance_distribution(
        db: Session,
        program_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        video_id: Optional[str] = None,
        topic_filter: Optional[str] = None,
        start_date=None,
        end_date=None,
    ) -> StanceDistributionOut:
        items = repository.get_stance_distribution(
            db,
            program_id=program_id,
            channel_id=channel_id,
            video_id=video_id,
            topic_filter=topic_filter,
            start_date=start_date,
            end_date=end_date,
        )
        total_valid = sum(i["count"] for i in items)
        return StanceDistributionOut(
            program_id=program_id,
            channel_id=channel_id,
            video_id=video_id,
            topic_filter=topic_filter,
            start_date=start_date,
            end_date=end_date,
            total_valid_comments=total_valid,
            distribution=[StanceDistributionItem(**i) for i in items],
        )

    @staticmethod
    def get_topic_stance_matrix(
        db: Session,
        program_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        video_id: Optional[str] = None,
        start_date=None,
        end_date=None,
    ) -> TopicStanceMatrixOut:
        matrix = repository.get_topic_stance_matrix(
            db,
            program_id=program_id,
            channel_id=channel_id,
            video_id=video_id,
            start_date=start_date,
            end_date=end_date,
        )
        return TopicStanceMatrixOut(
            program_id=program_id,
            channel_id=channel_id,
            video_id=video_id,
            matrix=matrix,
        )

    @staticmethod
    def get_entity_matrix(
        db: Session,
        entity_type: str = "program",
        matrix_type: str = "topic",
        channel_id: Optional[str] = None,
        start_date=None,
        end_date=None,
    ) -> EntityMatrixOut:
        if matrix_type == "stance":
            matrix = repository.get_entity_stance_matrix(
                db, entity_type=entity_type, channel_id=channel_id, start_date=start_date, end_date=end_date
            )
        else:
            matrix = repository.get_entity_topic_matrix(
                db, entity_type=entity_type, channel_id=channel_id, start_date=start_date, end_date=end_date
            )
        return EntityMatrixOut(entity_type=entity_type, matrix_type=matrix_type, matrix=matrix)

    @staticmethod
    def get_volume_over_time(
        db: Session,
        program_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        video_id: Optional[str] = None,
        granularity: str = "daily",
        start_date=None,
        end_date=None,
    ) -> VolumeOverTimeOut:
        points = repository.get_volume_over_time(
            db,
            program_id=program_id,
            channel_id=channel_id,
            video_id=video_id,
            granularity=granularity,
            start_date=start_date,
            end_date=end_date,
        )
        return VolumeOverTimeOut(
            program_id=program_id,
            channel_id=channel_id,
            video_id=video_id,
            granularity=granularity,
            data_points=[VolumeDataPoint(**p) for p in points],
        )

    @staticmethod
    def get_period_over_period(
        db: Session,
        program_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        period_days: int = 30,
    ) -> PeriodOverPeriodOut:
        data = repository.get_period_over_period_comparison(
            db, program_id=program_id, channel_id=channel_id, period_days=period_days
        )
        return PeriodOverPeriodOut(**data)

    @staticmethod
    def get_episode_analytics(
        db: Session,
        program_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> VideoAnalyticsOut:
        items = repository.get_video_episode_analytics(
            db, program_id=program_id, channel_id=channel_id, limit=limit, offset=offset
        )
        return VideoAnalyticsOut(
            items=[VideoAnalyticsItem(**i) for i in items],
            total=len(items),
        )

    @staticmethod
    def get_data_quality(
        db: Session,
        program_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        start_date=None,
        end_date=None,
    ) -> DataQualityAnalyticsOut:
        data = repository.get_data_quality_analytics(
            db, program_id=program_id, channel_id=channel_id, start_date=start_date, end_date=end_date
        )
        return DataQualityAnalyticsOut(**data)

    @staticmethod
    def get_faithfulness(
        db: Session,
        insight_id: Optional[str] = None,
        program_id: Optional[str] = None,
    ) -> FaithfulnessAnalyticsOut:
        data = repository.get_faithfulness_analytics(
            db, insight_id=insight_id, program_id=program_id
        )
        return FaithfulnessAnalyticsOut(**data)
