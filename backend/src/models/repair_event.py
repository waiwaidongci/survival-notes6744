from sqlalchemy import ForeignKey, String, Text, Double, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from ..config.database import Base


class RepairEvent(Base):
    """可修复灯带的复发事件流：故障 / 修复 / 永久退出。

    记录按接收顺序入库（received_seq 单调），事件时间可以乱序到达；
    分析时由 event_chain 状态机按 (event_time, received_seq) 重建工作区间。
    与终态 followup_events 相互独立，不改变旧研究口径。
    """
    __tablename__ = "repair_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    specimen_id: Mapped[int] = mapped_column(ForeignKey("specimens.id"))
    kind: Mapped[str] = mapped_column(String(16))            # failure | repair | withdrawal
    event_time: Mapped[float] = mapped_column(Double)        # 自启用累计小时
    received_seq: Mapped[int] = mapped_column(Integer)        # 接收序号（乱序到达的真实次序）
    note: Mapped[str] = mapped_column(Text, default="")


Index("repair_specimen_seq_idx", RepairEvent.specimen_id, RepairEvent.received_seq)
Index("repair_specimen_time_idx", RepairEvent.specimen_id, RepairEvent.event_time)
