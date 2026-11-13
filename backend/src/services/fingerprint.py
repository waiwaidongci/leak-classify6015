import hashlib,json
from src.constants.features import FEATURES
def fingerprint(rows,config):
 canonical=[{'id':r['id'],'reference':r['reference'],'features':{k:float(r['features'][k]) for k in sorted(FEATURES)},'label':int(r['label'])} for r in sorted(rows,key=lambda r:r['reference'])]
 return hashlib.sha256(json.dumps({'rows':canonical,'config':config,'algorithm':'logistic-pipeline-v2-sentinel','split_seed':73},sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()
def retest_fingerprint(rows,frozen,source_fingerprint):
 canonical=[{'id':r['id'],'reference':r['reference'],'features':{k:float(r['features'][k]) for k in sorted(FEATURES)},'label':int(r['label'])} for r in sorted(rows,key=lambda r:r['reference'])]
 sealed={'features':frozen['features'],'coefficients':[float(v) for v in frozen['coefficients']],'intercept':float(frozen['intercept']),'mean':[float(v) for v in frozen['mean']],'scale':[float(v) for v in frozen['scale']],'threshold':float(frozen['threshold']),'false_negative_cost':float(frozen['false_negative_cost']),'false_positive_cost':float(frozen['false_positive_cost'])}
 return hashlib.sha256(json.dumps({'rows':canonical,'sealed':sealed,'source_fingerprint':source_fingerprint,'algorithm':'sealed-retest-v1-apply-only'},sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()
