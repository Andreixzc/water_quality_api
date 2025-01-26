from enum import Enum


class AnalysisRequestStatusEnum(Enum):
    QUEUED = 1
    DOWNLOADING_IMAGES = 2
    PROCESSING_IMAGES = 3
    CANCELLED = 4
    FAILED = 5
    COMPLETED = 6
