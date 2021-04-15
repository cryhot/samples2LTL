import hashlib, base64
import json
from utils.Traces import parseExperimentTraces

# LEVELS
MINIMAL=0
BASIC=1
FULL=2

def hash_file(filename):
   """"This function returns the SHA-1 hash
   of the file passed into it"""
   h = hashlib.sha1()
   with open(filename,'rb') as file:
       chunk = 0
       while chunk != b'':
           chunk = file.read(1024)
           h.update(chunk)
   return h.hexdigest()

def microhash(s, length=8):
    return base64.b32encode(hashlib.sha1(str(s).encode("utf-8")).digest()).decode()[:length]

def json_flatten(data, keep_types=None):
    if not isinstance(data, dict): return data
    result = dict()
    for key, value in data.items():
        if isinstance(value, dict):
            for k, v in json_flatten(value, keep_types=keep_types).items():
                result[f'{key}.{k}'] = v
        elif keep_types is not None and not isinstance(value, keep_types):
            continue
        else:
            result[f'{key}'] = value
    return result


def json_traces_file(data={}, level=MINIMAL, **kwargs):
    result = dict()
    data = dict(data, **kwargs)
    if level<MINIMAL: return result
    result['filename'] = data['filename']
    result['sha1'] = hash_file(result['filename'])
    assert data.get('sha1') in (None, result['sha1']), "sha1 should be the same"
    if level<BASIC: return result
    traces = parseExperimentTraces(result['filename'])
    result['posTraces'] = len(traces.positive)
    result['negTraces'] = len(traces.negative)
    result['totTraces'] = len(traces)
    if isinstance(traces.numVariables, int): result['numVariables'] = traces.numVariables
    if level<FULL: return result
    result['traces'] = traces
    return result

def json_algo(*, name=None, args={}, level=BASIC,):
    result = dict()
    if level<MINIMAL: return result
    if name is not None: result['name'] = name
    if level>=BASIC:
        result['args'] = dict()
    for key, value in args.items():
        if level<FULL and not isinstance(value, (str,int,float,type(None))):
            continue
        result['args'][key] = value

    if level<BASIC: return result

    if level<FULL: return result
    return result
