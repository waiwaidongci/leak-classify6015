from datetime import datetime,timezone
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,JSON,ForeignKey,DateTime,UniqueConstraint
from src.config.database import Base
class RetestRun(Base):
 __tablename__='retest_runs'
 __table_args__=(UniqueConstraint('run_id','dataset_id'),)
 id:Mapped[int]=mapped_column(primary_key=True)
 run_id:Mapped[int]=mapped_column(ForeignKey('training_runs.id'))
 dataset_id:Mapped[int]=mapped_column(ForeignKey('window_datasets.id'))
 status:Mapped[str]=mapped_column(String(20),default='queued')
 result:Mapped[dict]=mapped_column(JSON,default=dict)
 error:Mapped[str|None]=mapped_column(String(1000),nullable=True)
 creator_id:Mapped[int]=mapped_column(ForeignKey('users.id'))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
