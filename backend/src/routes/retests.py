from fastapi import APIRouter,Depends,Response
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.dependencies import current_user,writers
from src.schemas.retest import RetestInput
from src.services import retests
router=APIRouter()
@router.get('/runs/{run_id}/retests')
def index(run_id:int,db:Session=Depends(get_db),user=Depends(current_user)):return retests.list_retests(db,run_id)
@router.post('/runs/{run_id}/retests',status_code=201)
def create(run_id:int,data:RetestInput,response:Response,db:Session=Depends(get_db),user=Depends(writers)):
 body,created=retests.create_retest(db,run_id,data,user)
 if not created: response.status_code=200
 return body
@router.post('/retests/{id}/retry')
def retry(id:int,db:Session=Depends(get_db),user=Depends(writers)):return retests.retry_retest(db,id,user)
