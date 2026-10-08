"""Import longer CRW comparative train/holdout records; do not read upstream test data."""
from pathlib import Path
import re
import zipfile
from .experimental_data import parse_bpseq,sequence_similarity
from .reference import digest


def overlaps(first,second,threshold=.8):
    if first==second:return True
    # Exact upper bound for SequenceMatcher ratio avoids impossible length matches.
    if 2*min(len(first),len(second))/(len(first)+len(second))<threshold:return False
    return sequence_similarity(first,second)>=threshold


def load_crw_development(root,config):
    root=Path(root).resolve()
    if type(config.get('min_length')) is not int or type(config.get('max_length')) is not int or not 1<=config['min_length']<=config['max_length']<=1024:raise ValueError('CRW development lengths must lie in1..1024')
    candidates={'train':[],'validation':[]};metadata={};sources={};rejected=[]
    for split,upstream,name in [('train','train','train_datasets/S-Processed-TRA.fasta'),('validation','holdout','holdout_datasets/S-Processed-VAL.fasta')]:
        path=root/'datasets_in_fasta_form'/name;content=path.read_bytes();sources[str(path)]=digest(content)
        header=None;sequence=[]
        def store():
            if header and 'EXT_SOURCE=Gutell Lab CRW;' in header:
                fields=dict(part.strip().split('=',1) for part in header.lstrip('> ').split(';'))
                key=(upstream,fields['SSTRAND_ID'],''.join(sequence))
                if key in metadata and metadata[key]!=fields:raise ValueError('Ambiguous CRW metadata binding')
                metadata[key]=fields
        for line in [*content.decode().splitlines(),'>end']:
            if line.startswith('>'):store();header=line;sequence=[]
            else:sequence.append(line.strip())
    path=root/'input_data.zip';sources[str(path)]=digest(path.read_bytes())
    with zipfile.ZipFile(path) as archive:
        for member in sorted(archive.namelist()):
            match=re.fullmatch(r'input_data/StructureData/(train|holdout)/CRW_[^/]+\.bpseq',member)
            if not match:continue
            identity=member.replace('/','_').removesuffix('.bpseq')
            try:
                content=archive.read(member);seq,structure=parse_bpseq(content.decode());upstream=match[1]
                fields=metadata.get((upstream,re.search(r'CRW_\d+',Path(member).stem).group(),seq))
                if fields is None:raise ValueError('No exact CRW source/sequence metadata match')
                if not config['min_length']<=len(seq)<=config['max_length']:raise ValueError('Outside fixed development length range')
                accessions=fields['EXT_ID'].split()
                if not accessions:raise ValueError('Missing upstream external identifier')
                split='train' if upstream=='train' else 'validation'
                candidates[split].append({'id':identity,'sequence':seq,'structure':structure,'reference_kind':'computational','source':'Processed comparative Gutell Lab CRW annotation via RNA STRAND/EternaFold; '+fields['EXT_ID'],'external_accessions':accessions,'external_id':fields['EXT_ID'],'rna_type':fields['TYPE'],'organism':fields['ORGANISM'],'rna_strand_id':fields['SSTRAND_ID'],'upstream_split':upstream,'bpseq_member':member,'bpseq_sha256':digest(content),'conditions':'Processed comparative annotation; no direct pair assay or record-specific experimental conditions inferred.'})
            except ValueError as exc:rejected.append({'id':identity,'reason':str(exc)})
    return candidates,{'source_sha256':sources,'candidate_counts':{s:len(rows) for s,rows in candidates.items()},'import_exclusions':rejected,'test_sources_read':False,'interpretation':'Comparative development annotations only; broad RNA types are retained, not assigned as verified families.'}


def select_crw(candidates,config,exposed,development=None):
    for split in ('train','validation'):
        if type(config.get(split+'_cap')) is not int or not 1<=config[split+'_cap']<=24:raise ValueError('Invalid bounded development cap')
    kept={};rejected=[];occupied=[]
    for split in ('validation','train'):
        rows=[]
        for record in sorted(candidates[split],key=lambda r:r['id']):
            if len(rows)>=config[split+'_cap']:
                rejected.append({'id':record['id'],'reason':'fixed_split_cap'});continue
            accessions={a.casefold() for a in record['external_accessions']}
            if any(overlaps(record['sequence'],r['sequence']) for r in exposed):
                rejected.append({'id':record['id'],'reason':'prior_sequence_exposure'});continue
            if any(accessions.intersection(a.casefold() for a in r.get('external_accessions',[])) or overlaps(record['sequence'],r['sequence']) for r in occupied):
                rejected.append({'id':record['id'],'reason':'accession_or_sequence_overlap'});continue
            if development and any(overlaps(record['sequence'],r['sequence']) for records in development.values() for r in records):
                rejected.append({'id':record['id'],'reason':'existing_development_overlap'});continue
            rows.append(record);occupied.append(record)
        if not rows:raise ValueError('Filtering left an empty CRW development split: '+split)
        kept[split]=rows
    return kept,rejected
