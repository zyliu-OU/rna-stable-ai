# Descriptive checkpoint-prior comparison

Previously exposed synthetic inputs; model/search seeds share sequences and are not independent biological samples.
Native selected energy is not labelled structure accuracy, biological stability, retained function or generalization.
All10000nt stack reference outcomes use the separately budgeted300-second frozen-finalist extension.1000/5000nt stack references used30 seconds and completed; helix studies used300 seconds for every length.
Matched successful outcomes do not imply equal runtime/cost. Extra reference requests and repeated controls retain separate budgets.
No best model/checkpoint/search seed is selected or deployed from this comparison. All outcomes, including inferior priors and input retention, remain reported.

| Helix model seed | Input | Search seed | Stack selected delta | Helix selected delta | Helix minus stack | Helix minus compatibility |
|---:|---|---:|---:|---:|---:|---:|
| 20261006 | synthetic_1000 | 20261006 | -18.5 | -21.0 | -2.5 | -12.599999999999966 |
| 20261006 | synthetic_1000 | 20261007 | -15.800000000000011 | -17.30000000000001 | -1.5 | -5.300000000000011 |
| 20261006 | synthetic_10000 | 20261006 | -2.399999999999636 | -5.899999999999636 | -3.5 | 0.20000000000027285 |
| 20261006 | synthetic_10000 | 20261007 | -6.599999999999909 | -17.899999999999636 | -11.299999999999727 | -12.599999999999909 |
| 20261006 | synthetic_5000 | 20261006 | -6.900000000000091 | -2.800000000000182 | 4.099999999999909 | -0.10000000000013642 |
| 20261006 | synthetic_5000 | 20261007 | -7.0 | -13.600000000000136 | -6.600000000000136 | -7.7000000000000455 |
| 20261007 | synthetic_1000 | 20261006 | -18.5 | -21.900000000000034 | -3.400000000000034 | -13.5 |
| 20261007 | synthetic_1000 | 20261007 | -15.800000000000011 | -15.0 | 0.8000000000000114 | -3.0 |
| 20261007 | synthetic_10000 | 20261006 | -2.399999999999636 | -5.899999999999636 | -3.5 | 0.20000000000027285 |
| 20261007 | synthetic_10000 | 20261007 | -6.599999999999909 | -17.899999999999636 | -11.299999999999727 | None |
| 20261007 | synthetic_5000 | 20261006 | -6.900000000000091 | -2.2000000000000455 | 4.7000000000000455 | 0.5 |
| 20261007 | synthetic_5000 | 20261007 | -7.0 | -11.600000000000136 | -4.600000000000136 | -5.7000000000000455 |

Replayed 24 model-independent controls with identical finalists and LinearFold energies.
