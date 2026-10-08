"""Python binding fallback for the CPU ViennaRNA MFE routine."""
import sys
import RNA
sequence = sys.stdin.readline().strip()
md = RNA.md()
md.temperature = float(sys.argv[1])
structure, energy = RNA.fold_compound(sequence, md).mfe()
print(sequence)
print(f'{structure} ({energy:.2f})')
