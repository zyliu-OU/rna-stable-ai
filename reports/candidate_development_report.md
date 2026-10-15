# Sparse candidate development diagnostics

Reused development labels and nine already selected checkpoints; no independent accuracy claim.
No fitting, checkpoint/decoder selection, native folds or prospective-panel access.
Legal reference pairs require canonical chemistry and endpoint distance >=4; excluded labels remain in the denominator.
Positive pairs outside the retained pool describe top-k pruning at the fixed original settings, not a new tuned candidate count.
Retained but unselected contacts describe scoring/structure competition; they do not establish a decoder error.

Contact counts are summed over records; F1 is a mean over records. Each reference contact appears in exactly one category.

| Seed | Head | Group | Records | Gold pairs | Illegal | Nonpositive | Positive pruned | Retained missed | Recovered | False positives | Mean F1 |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20261006 | baseline | all | 47 | 2351 | 7 | 0 | 1240 | 663 | 441 | 1612 | 0.38849854106861975 |
| 20261006 | baseline | PDB-derived | 12 | 107 | 0 | 0 | 11 | 27 | 69 | 53 | 0.6933184668666521 |
| 20261006 | baseline | Rfam-comparative | 23 | 623 | 0 | 0 | 74 | 273 | 276 | 490 | 0.39591621748678685 |
| 20261006 | baseline | CRW-comparative | 12 | 1621 | 7 | 0 | 1155 | 363 | 96 | 1069 | 0.06946140213576714 |
| 20261006 | helix | all | 47 | 2351 | 7 | 30 | 402 | 841 | 1071 | 1502 | 0.5244233333981245 |
| 20261006 | helix | PDB-derived | 12 | 107 | 0 | 0 | 3 | 33 | 71 | 52 | 0.7065040460628695 |
| 20261006 | helix | Rfam-comparative | 23 | 623 | 0 | 0 | 14 | 262 | 347 | 438 | 0.4951685501429536 |
| 20261006 | helix | CRW-comparative | 12 | 1621 | 7 | 30 | 385 | 546 | 653 | 1012 | 0.3984142886391238 |
| 20261006 | stack | all | 47 | 2351 | 7 | 59 | 731 | 898 | 656 | 1696 | 0.423379568067344 |
| 20261006 | stack | PDB-derived | 12 | 107 | 0 | 0 | 4 | 36 | 67 | 56 | 0.6798373793962029 |
| 20261006 | stack | Rfam-comparative | 23 | 623 | 0 | 0 | 24 | 320 | 279 | 500 | 0.4048003372245684 |
| 20261006 | stack | CRW-comparative | 12 | 1621 | 7 | 59 | 703 | 542 | 310 | 1140 | 0.20253194918713835 |
| 20261007 | baseline | all | 47 | 2351 | 7 | 27 | 1200 | 699 | 418 | 1392 | 0.37627740637695983 |
| 20261007 | baseline | PDB-derived | 12 | 107 | 0 | 0 | 6 | 34 | 67 | 55 | 0.6614137049618902 |
| 20261007 | baseline | Rfam-comparative | 23 | 623 | 0 | 0 | 41 | 306 | 276 | 500 | 0.3934341735815621 |
| 20261007 | baseline | CRW-comparative | 12 | 1621 | 7 | 27 | 1153 | 359 | 75 | 837 | 0.058257303983208567 |
| 20261007 | helix | all | 47 | 2351 | 7 | 7 | 757 | 745 | 835 | 1409 | 0.4950770012765886 |
| 20261007 | helix | PDB-derived | 12 | 107 | 0 | 0 | 4 | 30 | 73 | 49 | 0.7129503479878949 |
| 20261007 | helix | Rfam-comparative | 23 | 623 | 0 | 0 | 34 | 244 | 345 | 434 | 0.49131057188889204 |
| 20261007 | helix | CRW-comparative | 12 | 1621 | 7 | 7 | 719 | 471 | 417 | 926 | 0.2844226442250341 |
| 20261007 | stack | all | 47 | 2351 | 7 | 4 | 1061 | 786 | 493 | 1509 | 0.4010125156827184 |
| 20261007 | stack | PDB-derived | 12 | 107 | 0 | 0 | 4 | 36 | 67 | 55 | 0.6614137049618902 |
| 20261007 | stack | Rfam-comparative | 23 | 623 | 0 | 0 | 32 | 291 | 300 | 481 | 0.42670766094438467 |
| 20261007 | stack | CRW-comparative | 12 | 1621 | 7 | 4 | 1025 | 459 | 126 | 973 | 0.09136229798535286 |
| 20261008 | baseline | all | 47 | 2351 | 7 | 0 | 1305 | 615 | 424 | 1212 | 0.3932529810620268 |
| 20261008 | baseline | PDB-derived | 12 | 107 | 0 | 0 | 7 | 35 | 65 | 57 | 0.6480803716285568 |
| 20261008 | baseline | Rfam-comparative | 23 | 623 | 0 | 0 | 75 | 240 | 308 | 453 | 0.4432469261285743 |
| 20261008 | baseline | CRW-comparative | 12 | 1621 | 7 | 0 | 1223 | 340 | 51 | 702 | 0.042603862451280575 |
| 20261008 | helix | all | 47 | 2351 | 7 | 16 | 731 | 737 | 860 | 1363 | 0.49106862354687564 |
| 20261008 | helix | PDB-derived | 12 | 107 | 0 | 0 | 4 | 27 | 76 | 46 | 0.7327409592678679 |
| 20261008 | helix | Rfam-comparative | 23 | 623 | 0 | 0 | 39 | 266 | 318 | 453 | 0.45684299055258054 |
| 20261008 | helix | CRW-comparative | 12 | 1621 | 7 | 16 | 688 | 444 | 466 | 864 | 0.31499541773161577 |
| 20261008 | stack | all | 47 | 2351 | 7 | 0 | 1192 | 667 | 485 | 1367 | 0.4055479388678194 |
| 20261008 | stack | PDB-derived | 12 | 107 | 0 | 0 | 6 | 36 | 65 | 57 | 0.6480803716285568 |
| 20261008 | stack | Rfam-comparative | 23 | 623 | 0 | 0 | 67 | 242 | 314 | 454 | 0.44901980715860146 |
| 20261008 | stack | CRW-comparative | 12 | 1621 | 7 | 0 | 1119 | 389 | 106 | 856 | 0.07969442521641648 |
