"""Bind explicit protected coordinates to an exact input, without inferring biology."""
import copy
import hashlib
import json
from pathlib import Path
from .artifacts import sha256
from .optimization import check_constraints


def apply_constraints(config, sequence, path):
    path=Path(path).resolve()
    raw=path.read_bytes()
    spec=json.loads(raw)
    allowed={'schema_version','input_sha256','protected_positions','protected_regions'}
    if not isinstance(spec,dict) or set(spec)-allowed:
        raise ValueError('Unsupported constraint document fields')
    if type(spec.get('schema_version')) is not int or spec['schema_version']!=1:
        raise ValueError('Constraint schema_version must be 1')
    if spec.get('input_sha256')!=sha256(sequence):
        raise ValueError('Constraint input SHA256 does not match the FASTA sequence')
    positions=spec.get('protected_positions',[])
    if not isinstance(positions,list) or any(type(i) is not int or not 1<=i<=len(sequence) for i in positions):
        raise ValueError('Protected positions must be one-based integers within the input')
    regions=spec.get('protected_regions',[])
    if not isinstance(regions,list):
        raise ValueError('protected_regions must be a list')
    combined=set(config['protected_positions'])|set(positions)
    for region in regions:
        if not isinstance(region,dict) or set(region)-{'start','end','label'}:
            raise ValueError('Regions must contain start/end and an optional label')
        start,end=region.get('start'),region.get('end')
        if type(start) is not int or type(end) is not int or not 1<=start<=end<=len(sequence):
            raise ValueError('Regions require one-based inclusive start/end within the input')
        if 'label' in region and not isinstance(region['label'],str):
            raise ValueError('Region label must be a string')
        combined.update(range(start,end+1))
    result=copy.deepcopy(config)
    result['protected_positions']=sorted(combined)
    result['constraint_annotation']={'path':str(path),'file_sha256':hashlib.sha256(raw).hexdigest(),
        'schema_version':1,'input_sha256':sha256(sequence),'coordinate_system':'one_based_inclusive',
        'protected_regions':regions,'protected_position_count':len(combined)}
    check_constraints(sequence,sequence,result)
    return result
