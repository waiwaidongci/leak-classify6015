from pydantic import BaseModel,Field
class RetestInput(BaseModel):
 dataset_id:int=Field(gt=0)
