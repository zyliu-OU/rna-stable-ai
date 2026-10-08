# Exact sparse development comparison

Identical exposed development records and candidates. Exact maximum summed logits under noncrossing constraints, not maximum label agreement or unrestricted pair search. Bounded to1024 nt/64 candidates per endpoint. No fitting or fresh test.

| Model | Group | Decoder | Records | Mean pair F1 | Mean logit objective |
|---|---|---|---:|---:|---:|
| trained_expanded_sparse | all | greedy | 47 | 0.1407018641905426 | 29.45641081447297 |
| trained_expanded_sparse | all | refined | 47 | 0.20857850721519425 | 33.740908401443605 |
| trained_expanded_sparse | all | exact_sparse | 47 | 0.342535080846632 | 40.060072577063075 |
| trained_expanded_sparse | PDB-derived annotation | greedy | 12 | 0.3838841713841714 | 24.443362119297188 |
| trained_expanded_sparse | PDB-derived annotation | refined | 12 | 0.5622727175358754 | 28.470229104161263 |
| trained_expanded_sparse | PDB-derived annotation | exact_sparse | 12 | 0.6806178026766262 | 31.97589456786712 |
| trained_expanded_sparse | Rfam comparative | greedy | 23 | 0.07265295628779263 | 27.24666307218697 |
| trained_expanded_sparse | Rfam comparative | refined | 23 | 0.10762048692752478 | 31.406381054416947 |
| trained_expanded_sparse | Rfam comparative | exact_sparse | 23 | 0.29725327247702216 | 38.120016268414 |
| trained_expanded_sparse | CRW comparative | greedy | 12 | 0.027946630477184587 | 38.704809349030256 |
| trained_expanded_sparse | CRW comparative | refined | 12 | 0.04838716911254617 | 43.486098447193704 |
| trained_expanded_sparse | CRW comparative | exact_sparse | 12 | 0.09124249172505657 | 51.86269184450308 |
| trained_sampled_sparse | all | greedy | 47 | 0.16892827657306964 | 39.62177299232559 |
| trained_sampled_sparse | all | refined | 47 | 0.20172616105030025 | 43.46458495059546 |
| trained_sampled_sparse | all | exact_sparse | 47 | 0.23460531347731278 | 47.61734664709644 |
| trained_sampled_sparse | PDB-derived annotation | greedy | 12 | 0.5154780805709599 | 17.634390644729137 |
| trained_sampled_sparse | PDB-derived annotation | refined | 12 | 0.5815512095117358 | 18.17781274020672 |
| trained_sampled_sparse | PDB-derived annotation | exact_sparse | 12 | 0.6315505565699064 | 18.50049811353286 |
| trained_sampled_sparse | Rfam comparative | greedy | 23 | 0.058790993715267054 | 28.4840658252006 |
| trained_sampled_sparse | Rfam comparative | refined | 23 | 0.07731531795060397 | 30.884919025651786 |
| trained_sampled_sparse | Rfam comparative | exact_sparse | 23 | 0.09919659083689489 | 33.19801564903363 |
| trained_sampled_sparse | CRW comparative | greedy | 12 | 0.033474931385967736 | 82.95642741024494 |
| trained_sampled_sparse | CRW comparative | refined | 12 | 0.06035522852994927 | 92.86238351712625 |
| trained_sampled_sparse | CRW comparative | exact_sparse | 12 | 0.09719345544552005 | 104.37124626028042 |
