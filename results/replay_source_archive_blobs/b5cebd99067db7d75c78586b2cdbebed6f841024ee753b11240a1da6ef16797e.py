"""Bounded worker for evaluating a fixed structure with current ViennaRNA parameters."""
import json
import sys
import RNA
from .sequences import validate_sequence
from .scoring import paired_fraction
item = json.loads(sys.stdin.readline())
validate_sequence(item['sequence'])
paired_fraction(item['structure'], len(item['sequence']))
md = RNA.md()
md.temperature = float(item.get('temperature_c', 37))
md.dangles = 2
fc = RNA.fold_compound(item['sequence'], md, RNA.OPTION_EVAL_ONLY)
print(json.dumps({'energy_kcal_mol': float(fc.eval_structure(item['structure'])), 'viennarna_version': RNA.__version__}))
