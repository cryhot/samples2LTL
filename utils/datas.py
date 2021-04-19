import hashlib, base64
import json
from utils.Traces import parseExperimentTraces

# LEVELS
MINIMAL=0
BASIC=1
FULL=2

class Data(dict):
    """
    Access by data['key'] or data.key
    Subkeys like data['key']['subkey'] can also be accessed by data['key.subkey']
    Can be used with json: json.load(..., object_hook=Data)
    """
    def __getitem__(self, key):
        key = key.split(".", 1)
        if len(key) == 1:
            if key[0] not in self.keys(): return None
            return super().__getitem__(key[0])
        return super().__getitem__(key[0]).__getitem__(key[1])
    def __setitem__(self, key, value):
        key = key.split(".", 1)
        if len(key) == 1:
            return super().__setitem__(key[0], value)
        return super().__getitem__(key[0]).__setitem__(key[1], value)
    def __delitem__(self, key):
        key = key.split(".", 1)
        if len(key) == 1:
            if key[0] not in self.keys(): return None
            return super().__delitem__(key[0])
        return super().__getitem__(key[0]).__delitem__(key[1])
    def __getattr__(self, *arg,**kwd):
        return self.__getitem__(*arg,**kwd)
    def __setattr__(self, *arg,**kwd):
        return self.__setitem__(*arg,**kwd)
    def __delattr__(self, *arg,**kwd):
        return self.__delitem__(*arg,**kwd)


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
    result = Data()
    data = dict(data, **kwargs)
    if level<MINIMAL: return result
    result['filename'] = data['filename']
    result['sha1'] = hash_file(result['filename'])
    assert data.get('sha1') in (None, result['sha1']), f"file has changed: {result['filename']}"
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
    result = Data()
    if level<MINIMAL: return result
    if name is not None: result['name'] = name
    if level>=BASIC:
        result['args'] = Data()
    for key, value in args.items():
        if level<FULL and not isinstance(value, (str,int,float,type(None))):
            continue
        result['args'][key] = value

    if level<BASIC: return result

    if level<FULL: return result
    return result
