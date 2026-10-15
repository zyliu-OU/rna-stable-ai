#!/usr/bin/env python3
"""Plot audited pilot diagnostics without training or changing measured evidence."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.artifacts import timestamp, write_artifact
from rnastable.reference import digest
from verify_experimental_pilot import audit_pilot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, default=ROOT/'results/experimental_pilot_summary.json')
    args = parser.parse_args()
    summary = audit_pilot(args.summary)
    os.environ.setdefault('MPLCONFIGDIR', str(ROOT/'.cache/rnastable-matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    history = summary['training']['history']
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), layout='constrained')
    epochs = [r['epoch'] for r in history]
    axes[0].plot(epochs, [r['mean_train_loss'] for r in history], label='Train')
    axes[0].plot(epochs, [r['validation_mean_loss'] for r in history], label='Validation')
    axes[0].set(title='Loss per record', xlabel='Epoch', ylabel='Weighted cross entropy'); axes[0].legend()
    axes[1].plot(epochs, [r['validation_mean_pair_f1'] for r in history])
    axes[1].axvline(summary['training']['selected_epoch'], color='tab:red', linestyle='--', label='Selected')
    axes[1].set(title='Validation checkpoint selection', xlabel='Epoch', ylabel='Mean exact-pair F1', ylim=(0, 1)); axes[1].legend()
    groups = summary['aggregates']
    axes[2].barh([r['method'] for r in groups], [r['mean_pair_f1'] or 0 for r in groups])
    axes[2].set(title='Test: 16 processed PDB references', xlabel='Mean exact-pair F1', xlim=(0, 1))
    fig.suptitle('RNA-StableAI first training pilot — short processed annotations; one seed')
    directory = Path(summary['run_dir'])/'figures'/timestamp()
    directory.mkdir(parents=True, exist_ok=False)
    figure = directory/'diagnostics.png'
    fig.savefig(figure, dpi=180); plt.close(fig)
    metadata = {'source_summary': str(args.summary.resolve()), 'source_sha256': digest(args.summary.read_bytes()),
                'figure': str(figure), 'figure_sha256': digest(figure.read_bytes()),
                'interpretation': 'Validation selected the checkpoint; test results were not used for tuning. Processed PDB annotations are not biological stability measurements.'}
    (directory/'manifest.json').write_text(json.dumps(metadata, indent=2)+'\n')
    write_artifact(ROOT/'results/experimental_pilot_diagnostics_summary.json', json.dumps(metadata, indent=2)+'\n')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
