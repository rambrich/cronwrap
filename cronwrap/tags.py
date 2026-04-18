"""Tag-based filtering and labeling for cron job runs."""
from dataclasses import dataclass, field
from typing import List, Optional
import os


@dataclass
class TagConfig:
    tags: List[str] = field(default_factory=list)
    filter_tags: List[str] = field(default_factory=list)
    enabled: bool = False

    @classmethod
    def from_env(cls) -> "TagConfig":
        raw_tags = os.environ.get("CRONWRAP_TAGS", "")
        raw_filter = os.environ.get("CRONWRAP_FILTER_TAGS", "")
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        filter_tags = [t.strip() for t in raw_filter.split(",") if t.strip()]
        enabled = bool(tags or filter_tags)
        return cls(tags=tags, filter_tags=filter_tags, enabled=enabled)


def parse_tags(raw: str) -> List[str]:
    """Parse a comma-separated tag string into a list."""
    return [t.strip() for t in raw.split(",") if t.strip()]


def matches_filter(tags: List[str], filter_tags: List[str]) -> bool:
    """Return True if any tag matches the filter, or filter is empty."""
    if not filter_tags:
        return True
    return bool(set(tags) & set(filter_tags))


@dataclass
class TagManager:
    config: TagConfig

    def should_run(self, job_tags: Optional[List[str]] = None) -> bool:
        """Check if a job with given tags should run given the filter."""
        if not self.config.enabled:
            return True
        tags = job_tags or []
        return matches_filter(tags, self.config.filter_tags)

    def annotate(self, data: dict) -> dict:
        """Add configured tags to a data dict."""
        if self.config.tags:
            data["tags"] = self.config.tags
        return data
