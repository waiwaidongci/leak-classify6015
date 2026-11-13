from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from src.models import TrainingRun,RetestRun,WindowDataset,SensorWindow
from src.utils.serialize import row
from src.constants.enums import RunStatus
from .audit import record
from .retest_apply import frozen_parameters

def list_retests(db,run_id): return [row(x) for x in db.scalars(select(RetestRun).where(RetestRun.run_id==run_id).order_by(RetestRun.id.desc()))]
def get_retest(db,id):
 obj=db.get(RetestRun,id)
 if not obj: raise HTTPException(404,'复测任务不存在')
 return obj
def split_references(db,frozen):
 ids=[i for part in frozen['split_ids'].values() for i in part]
 return set(db.scalars(select(SensorWindow.reference).where(SensorWindow.id.in_(ids))))
def sealed_run(db,run_id):
 run=db.get(TrainingRun,run_id)
 if not run: raise HTTPException(404,'训练运行不存在')
 if run.status!=RunStatus.SUCCEEDED: raise HTTPException(422,'仅已封存的研究可发起复测')
 try: frozen=frozen_parameters(run)
 except ValueError as e: raise HTTPException(422,str(e))
 return run,frozen
def reject_overlap(db,frozen,dataset_id):
 overlap=split_references(db,frozen)&set(db.scalars(select(SensorWindow.reference).where(SensorWindow.dataset_id==dataset_id)))
 if overlap: raise HTTPException(409,f'复测数据与原研究分割存在 {len(overlap)} 个重名窗口（如 {sorted(overlap)[0]}），整次复测拒绝，旧样本不得冒充外部验证')
def create_retest(db,run_id,data,user):
 run,frozen=sealed_run(db,run_id)
 if not db.get(WindowDataset,data.dataset_id): raise HTTPException(404,'数据集不存在')
 reject_overlap(db,frozen,data.dataset_id)
 existing=db.scalar(select(RetestRun).where(RetestRun.run_id==run_id,RetestRun.dataset_id==data.dataset_id))
 if existing: return row(existing),False
 obj=RetestRun(run_id=run_id,dataset_id=data.dataset_id,creator_id=user.id);db.add(obj)
 try: db.commit()
 except IntegrityError:
  db.rollback();return row(db.scalar(select(RetestRun).where(RetestRun.run_id==run_id,RetestRun.dataset_id==data.dataset_id))),False
 from src.worker import retest_run
 try: retest_run.delay(obj.id)
 except Exception:
  obj.status=RunStatus.FAILED;obj.error='队列不可用，请重试';db.commit();raise HTTPException(503,obj.error)
 record(db,user.email,'retest.queued',{'retest_id':obj.id,'run_id':run_id,'dataset_id':data.dataset_id});return row(obj),True
def retry_retest(db,id,user):
 obj=get_retest(db,id)
 if obj.status==RunStatus.SUCCEEDED: raise HTTPException(409,'已完成的复测保持原样，不可重跑')
 if obj.status!=RunStatus.FAILED: raise HTTPException(409,'任务已在队列或执行中，无需重试')
 obj.status=RunStatus.QUEUED;obj.error=None;db.commit()
 from src.worker import retest_run
 try: retest_run.delay(obj.id)
 except Exception:
  obj.status=RunStatus.FAILED;obj.error='队列不可用，请重试';db.commit();raise HTTPException(503,obj.error)
 record(db,user.email,'retest.requeued',{'retest_id':id});return row(obj)
