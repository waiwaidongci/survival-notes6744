from sqlalchemy import ForeignKey, String, JSON, Text, Double
from sqlalchemy.orm import Mapped, mapped_column
from ..config.database import Base
from ..utils.clock import now


class RecurrentRun(Base):
    """复发事件（平均累计故障函数 MCF）研究：两批可修复灯带的累计故障比较。"""
    __tablename__ = "recurrent_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    cohort_a_id: Mapped[int] = mapped_column(ForeignKey("test_cohorts.id"))
    cohort_b_id: Mapped[int] = mapped_column(ForeignKey("test_cohorts.id"))
    cutoff_hours: Mapped[float] = mapped_column(Double, default=1450.)
    confidence: Mapped[float] = mapped_column(Double, default=.95)
    status: Mapped[str] = mapped_column(String(24), default="queued")
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[str] = mapped_column(String(64), default=now)
