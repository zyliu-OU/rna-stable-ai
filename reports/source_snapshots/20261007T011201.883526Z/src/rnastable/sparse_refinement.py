"""Bounded local exchanges improve a sparse greedy structure without claiming global optimality."""
import itertools
import numpy as np
from .global_sparse_pairs import decode_sparse
from .scoring import base_pairs


def conflict_indices(i,j,pairs,indices):
    a,b=pairs[indices,0],pairs[indices,1]
    mask=(a==i)|(a==j)|(b==i)|(b==j)|((a<i)&(i<b)&(b<j))|((i<a)&(a<j)&(j<b))
    return indices[mask]


def compatible(first,second):
    i,j=first;k,l=second
    return len({int(i),int(j),int(k),int(l)})==4 and not (i<k<j<l or k<i<l<j)


def refine_sparse(sequence,pairs,scores,passes=2,max_remove=2,group_cap=8,include_subsets=False):
    if type(passes) is not int or not 1<=passes<=4 or type(max_remove) is not int or not 1<=max_remove<=2 or type(group_cap) is not int or not 2<=group_cap<=16:raise ValueError('Invalid bounded refinement settings')
    if type(include_subsets) is not bool:raise ValueError('Subset grouping flag must be boolean')
    greedy=decode_sparse(sequence,pairs,scores);pairs=np.asarray(pairs);scores=np.asarray(scores,dtype=float)
    index={tuple(pair):offset for offset,pair in enumerate(pairs)}
    if len(index)!=len(pairs):raise ValueError('Refinement requires unique candidate pairs')
    selected=np.zeros(len(pairs),dtype=bool)
    for pair in base_pairs(greedy['structure']):selected[index[pair]]=True
    active=set(map(int,np.flatnonzero(selected)))
    objective=float(scores[selected].sum());history=[objective];moves=0;discarded=0
    order=np.lexsort((pairs[:,1],pairs[:,0],-scores))
    for _ in range(passes):
        groups={};proposals=[];current=np.array(sorted(active),dtype=np.int64)
        for offset in order:
            if selected[offset] or scores[offset]<=0:continue
            i,j=pairs[offset];conflicts=conflict_indices(i,j,pairs,current)
            if not len(conflicts):
                proposals.append((float(scores[offset]),(),(int(offset),)));continue
            if len(conflicts)>max_remove:continue
            key=tuple(map(int,conflicts));group=groups.setdefault(key,[])
            if len(group)<group_cap:group.append(int(offset))
            else:discarded+=1
        blockers={p:key for key,group in groups.items() for p in group}
        for removed,group in groups.items():
            pool=list(group)
            if include_subsets and len(removed)==2:
                pool.extend(groups.get((removed[0],),[]));pool.extend(groups.get((removed[1],),[]))
            best=None
            for added in itertools.chain(((p,) for p in pool),itertools.combinations(pool,2)):
                if len(added)==2 and not compatible(pairs[added[0]],pairs[added[1]]):continue
                actual_removed=tuple(sorted(set().union(*(blockers[p] for p in added))))
                gain=float(scores[list(added)].sum())-float(scores[list(actual_removed)].sum())
                if gain>1e-8 and (best is None or gain>best[0]):best=(gain,actual_removed,added)
            if best is not None:proposals.append(best)
        proposals.sort(key=lambda p:(-p[0],p[1],p[2]));accepted=0
        for gain,removed,added in proposals:
            if any(not selected[p] for p in removed) or any(selected[p] for p in added):continue
            remaining=active.difference(removed);current=np.fromiter(remaining,dtype=np.int64)
            valid=all(not len(conflict_indices(*pairs[p],pairs,current)) for p in added)
            if valid:
                selected[list(removed)]=False;selected[list(added)]=True
                active=remaining.union(added);accepted+=1;moves+=1
        if not accepted:break
        updated=float(scores[selected].sum())
        if updated<objective-1e-8:raise ValueError('Refinement objective decreased')
        objective=updated;history.append(objective)
    structure=['.']*len(sequence)
    for i,j in pairs[selected]:structure[i],structure[j]='(',')'
    result={'structure':''.join(structure),'objective':objective,'accepted_pairs':int(selected.sum()),
            'greedy_objective':history[0],'objective_history':history,'accepted_moves':moves,
            'group_cap_discarded_candidates':discarded,'passes':passes,'max_remove':max_remove,'group_cap':group_cap,
            'interpretation':'Approximate local replacement of at most two pairs by one/two candidates; strictly improving moves, fixed passes/group cap; not global optimization.'}

    if include_subsets:
        result['include_subsets']=True
        result['interpretation']='Approximate local exchanges combine candidates blocked by subsets of at most two removed pairs; fixed passes/group cap; not global optimization.'
    return result
