import json
from pathlib import Path
from celery import Celery
from src.config.settings import REDIS_URL,ARTIFACT_DIR
from src.config.database import SessionLocal
from src.models import TrainingRun,RetestRun
from src.services.datasets import get_windows
from src.services.training import train_model
from src.services.retest_apply import frozen_parameters,apply_sealed_model
from src.services.retests import split_references
from src.services.audit import record
from src.constants.enums import RunStatus
app=Celery('leak_classify',broker=REDIS_URL,backend=REDIS_URL)
app.conf.update(task_track_started=True,worker_prefetch_multiplier=1,task_acks_late=True)
@app.task(name='leak.train',soft_time_limit=180,time_limit=210)
def train_run(id):
 with SessionLocal() as db:
  run=db.get(TrainingRun,id)
  if not run or run.status==RunStatus.SUCCEEDED:return
  run.status=RunStatus.RUNNING;db.commit()
  try:
   result=train_model(get_windows(db,run.dataset_id),run.config)
   Path(ARTIFACT_DIR).mkdir(parents=True,exist_ok=True);Path(ARTIFACT_DIR,f'training-{id}.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False))
   run.result=result;run.status=RunStatus.SUCCEEDED;run.error=None;db.commit();record(db,'worker','training.succeeded',{'run_id':id,'test_auc':result['test']['auc']})
  except Exception as e:
   db.rollback();run=db.get(TrainingRun,id);run.status=RunStatus.FAILED;run.error=str(e)[:1000];db.commit();record(db,'worker','training.failed',{'run_id':id,'error':run.error})
@app.task(name='leak.retest',soft_time_limit=180,time_limit=210)
def retest_run(id):
 with SessionLocal() as db:
  retest=db.get(RetestRun,id)
  # Succeeded re-tests are sealed: a duplicate delivery never adds a new result.
  if not retest or retest.status==RunStatus.SUCCEEDED:return
  retest.status=RunStatus.RUNNING;db.commit()
  try:
   run=db.get(TrainingRun,retest.run_id)
   if not run or run.status!=RunStatus.SUCCEEDED: raise ValueError('原研究不存在或未封存，禁止复测')
   frozen=frozen_parameters(run)
   rows=get_windows(db,retest.dataset_id)
   overlap=split_references(db,frozen)&{r['reference'] for r in rows}
   if overlap: raise ValueError(f'复测数据与原研究分割存在 {len(overlap)} 个重名窗口，整次复测拒绝')
   result=apply_sealed_model(frozen,rows,run.result.get('fingerprint',''))
   Path(ARTIFACT_DIR).mkdir(parents=True,exist_ok=True);Path(ARTIFACT_DIR,f'retest-{id}.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False))
   retest.result=result;retest.status=RunStatus.SUCCEEDED;retest.error=None;db.commit();record(db,'worker','retest.succeeded',{'retest_id':id,'auc':result['summary']['auc']})
  except Exception as e:
   db.rollback();retest=db.get(RetestRun,id);retest.status=RunStatus.FAILED;retest.error=str(e)[:1000];db.commit();record(db,'worker','retest.failed',{'retest_id':id,'error':retest.error})
