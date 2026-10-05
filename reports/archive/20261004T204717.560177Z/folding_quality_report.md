# Folding-quality comparison

Agreement with a computational reference, not experimental structure accuracy. Energy models can differ; reevaluation uses current ViennaRNA parameters with dangles=2.

| Sequence | Reference | Status | LF reported gap kcal/mol | LF reevaluated gap kcal/mol | Pair F1 | Pair distance |
|---|---|---|---:|---:|---:|---:|
| structured_1000_seed1729 | saved | ok | 0.0 | -2.4414062522737368e-05 | 0.9976415094339622 | 2 |
| mixed_1000_seed1729 | saved | ok | 7.699999999999989 | 7.699999999999989 | 0.4845679012345679 | 334 |
| structured_2000_seed1729 | saved | ok | 0.0 | 4.8828125045474735e-05 | 0.9988207547169812 | 2 |
| mixed_2000_seed1729 | saved | ok | 19.0 | 19.0 | 0.4499599679743795 | 687 |
| structured_5000_seed1729 | saved | ok | 1.199999999999818 | 1.200097656249909 | 0.9833684703677676 | 71 |
| mixed_5000_seed1729 | saved | ok | 47.5 | 47.499951171874955 | 0.5464649583204693 | 1469 |
| structured_10000_seed1729 | saved | ok | 20.300000000000182 | 20.2998046875 | 0.9402090919769764 | 509 |
| mixed_10000_seed1729 | retry | ok | 92.5 | 92.5 | 0.5242807124372051 | 3125 |

All folds and fixed-structure evaluations use CPU. Gaps are LinearFold minus ViennaRNA; lower gaps mean closer energies. Matching energies need not mean matching structures. No biological validation or training was performed.

Sources: [ViennaRNA structure evaluation](https://viennarna.readthedocs.io/en/latest/eval/eval_structures.html), [LinearFold](https://github.com/LinearFold/LinearFold).
