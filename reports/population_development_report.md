# Population-sampled helix development comparison

Full-supervision control F1: 0.5244233333981245

| Sampling seed | Model seed | Selected epoch | Reused validation F1 | Sampled negatives | Full negatives | Retained tensor bytes |
|---:|---:|---:|---:|---:|---:|---:|
| 20261006 | 20261006 | 5 | 0.5251274372714272 | 136538 | 1180545 | 2820000 |
| 20261007 | 20261006 | 5 | 0.5195605741107528 | 136538 | 1180545 | 2820000 |
| 20261008 | 20261006 | 5 | 0.5244995276237349 | 136538 | 1180545 | 2820000 |

Reused frozen89 train/47 validation records; no fresh test or generalization claim.
Each fit reuses one draw across10 epochs; expectation-unbiased sampled loss does not imply equivalent optimization.
Sampling seeds vary while model initialization remains fixed. No selection over sampling seeds is performed.
Exact decoding/full validation remain bounded to1024nt; long synthetic sampling does not establish long biological accuracy.
