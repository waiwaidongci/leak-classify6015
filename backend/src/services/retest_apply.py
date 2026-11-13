import numpy as np
from src.constants.features import FEATURES
from .metrics import evaluate
from .fingerprint import retest_fingerprint

INCOMPLETE='原研究封存参数不全（标准化/系数/阈值/成本/分割索引），明确拒绝复测；系统不补训、不重选阈值'

def frozen_parameters(run):
 # Sealed studies only: every value needed to replay the decision must already
 # exist in the stored result/config. Nothing is refit or re-derived here.
 result=run.result or {};config=run.config or {}
 try:
  coefficients=[(str(c['feature']),float(c['coefficient'])) for c in result['coefficients']]
  intercept=float(result['intercept'])
  mean=[float(v) for v in result['standardization']['mean']]
  scale=[float(v) for v in result['standardization']['scale']]
  threshold=float(result['recommendation']['threshold'])
  fn_cost=float(config['false_negative_cost']);fp_cost=float(config['false_positive_cost'])
  split_ids={k:[int(i) for i in v] for k,v in result['split_ids'].items()}
 except (KeyError,TypeError,ValueError,AttributeError): raise ValueError(INCOMPLETE)
 features=[f for f,_ in coefficients]
 if not features or not set(features)<=set(FEATURES) or len(set(features))!=len(features): raise ValueError(INCOMPLETE)
 values=np.asarray([v for _,v in coefficients]+[intercept]+mean+scale+[threshold,fn_cost,fp_cost],dtype=float)
 if not np.isfinite(values).all(): raise ValueError(INCOMPLETE)
 if len(mean)!=len(features) or len(scale)!=len(features) or any(s<=0 for s in scale): raise ValueError(INCOMPLETE)
 if fn_cost<=0 or fp_cost<=0: raise ValueError(INCOMPLETE)
 if not split_ids or any(not v for v in split_ids.values()): raise ValueError(INCOMPLETE)
 return {'features':features,'coefficients':[v for _,v in coefficients],'intercept':intercept,'mean':mean,'scale':scale,'threshold':threshold,'false_negative_cost':fn_cost,'false_positive_cost':fp_cost,'split_ids':split_ids}

def apply_sealed_model(frozen,rows,source_fingerprint):
 # Apply-only path: frozen standardization, frozen logit, frozen threshold and
 # costs. No fitting, no CV, no threshold search — those belong to the study.
 rows=sorted(rows,key=lambda r:r['reference'])
 if not rows: raise ValueError('复测数据集没有窗口')
 if len({r['reference'] for r in rows})!=len(rows): raise ValueError('窗口自然键重复')
 if any(set(r['features'])!=set(FEATURES) or r['label'] not in (0,1) for r in rows): raise ValueError('特征/标签模式不合法')
 X=np.asarray([[r['features'][f] for f in frozen['features']] for r in rows],dtype=float)
 if not np.isfinite(X).all(): raise ValueError('特征含非有限值')
 z=(X-np.asarray(frozen['mean']))/np.asarray(frozen['scale'])
 logit=z@np.asarray(frozen['coefficients'])+frozen['intercept']
 p=1/(1+np.exp(-logit));threshold=frozen['threshold']
 y=np.asarray([r['label'] for r in rows],dtype=int)
 summary=evaluate(y,p,threshold,frozen['false_negative_cost'],frozen['false_positive_cost'])
 predictions=[{'window_id':r['id'],'reference':r['reference'],'probability':float(s),'predicted':int(s>=threshold)} for r,s in zip(rows,p)]
 frozen_echo={k:frozen[k] for k in ('features','coefficients','intercept','mean','scale','threshold','false_negative_cost','false_positive_cost')}
 return {'fingerprint':retest_fingerprint(rows,frozen,source_fingerprint),'source_fingerprint':source_fingerprint,'frozen':frozen_echo,'n_windows':len(rows),'positive':int(y.sum()),'summary':summary,'predictions':predictions,'method':'apply-only replay of the sealed pipeline: frozen standardization, frozen logistic score, frozen validation threshold and costs; no refit, no threshold re-selection','assumption':'External windows are judged by the sealed study as-is; distribution shift is reported, never corrected.'}
