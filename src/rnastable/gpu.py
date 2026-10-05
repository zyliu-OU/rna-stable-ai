"""Untrained embedding + Conv1d encoder; linear sequence memory, no attention."""
import json
import platform
import statistics
import sys
import time
from .sequences import generate_sequence

FIELDS = ['length', 'batch_size', 'status', 'cpu_seconds', 'gpu_seconds',
          'transfer_seconds', 'peak_gpu_memory_mib', 'gpu_reserved_mib', 'repeats',
          'cpu_threads', 'torch_version', 'cuda_build', 'cuda_available', 'gpu_name',
          'python_version', 'error']

def benchmark_gpu(config):
    rows = []
    try:
        import torch
    except Exception as exc:
        return [dict(length=n, batch_size=config['batch_size'], status='skipped',
                     cuda_available=False, python_version=platform.python_version(),
                     error=f'{type(exc).__name__}: {exc}') for n in config['lengths']]
    torch.manual_seed(config['seed'])
    torch.set_num_threads(config['cpu_threads'])
    available = torch.cuda.is_available()
    class Encoder(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.embedding = torch.nn.Embedding(4, config['embedding_dim'])
            self.conv = torch.nn.Conv1d(config['embedding_dim'], config['channels'], 7, padding=3)
            self.activation = torch.nn.GELU()
            self.output = torch.nn.Linear(config['channels'], 1)
        def forward(self, x):
            x = self.embedding(x).transpose(1, 2)
            return self.output(self.activation(self.conv(x)).mean(dim=-1))
    model_cpu = Encoder().eval()
    model_gpu = None
    gpu_error = 'CUDA unavailable; GPU timing, transfer and memory left blank'
    if available:
        try:
            import copy
            model_gpu = copy.deepcopy(model_cpu).to('cuda').eval()
        except Exception as exc:
            gpu_error = f'{type(exc).__name__}: {exc}'
    with torch.inference_mode():
        for n in config['lengths']:
            row = dict(length=n, batch_size=config['batch_size'], status='skipped',
                       repeats=config['repeats'], cpu_threads=config['cpu_threads'],
                       torch_version=torch.__version__, cuda_build=torch.version.cuda,
                       cuda_available=available, python_version=platform.python_version(), error=gpu_error)
            try:
                sequence = generate_sequence(n, 'mixed', config['seed'])
                x = torch.tensor([['ACGU'.index(c) for c in sequence]] * config['batch_size'], dtype=torch.long)
                for _ in range(config['warmup']):
                    model_cpu(x)
                timings = []
                for _ in range(config['repeats']):
                    start = time.perf_counter(); model_cpu(x); timings.append(time.perf_counter()-start)
                row['cpu_seconds'] = statistics.median(timings)
                if model_gpu is not None:
                    row['gpu_name'] = torch.cuda.get_device_name(0)
                    host = x.pin_memory()
                    # Preallocated destination: measure H2D copy only, using CUDA events.
                    device = torch.empty_like(host, device='cuda')
                    for _ in range(config['warmup']):
                        device.copy_(host, non_blocking=True); model_gpu(device)
                    torch.cuda.synchronize()
                    torch.cuda.reset_peak_memory_stats()
                    transfers, forwards = [], []
                    for _ in range(config['repeats']):
                        a, b, c = [torch.cuda.Event(enable_timing=True) for _ in range(3)]
                        a.record(); device.copy_(host, non_blocking=True); b.record()
                        model_gpu(device); c.record(); c.synchronize()
                        transfers.append(a.elapsed_time(b)/1000)
                        forwards.append(b.elapsed_time(c)/1000)
                    row.update(status='ok', error='', transfer_seconds=statistics.median(transfers),
                               gpu_seconds=statistics.median(forwards),
                               peak_gpu_memory_mib=torch.cuda.max_memory_allocated()/1024**2,
                               gpu_reserved_mib=torch.cuda.max_memory_reserved()/1024**2)
                    del device, host
            except Exception as exc:
                row.update(status='error', error=f'{type(exc).__name__}: {exc}')
                if available:
                    torch.cuda.empty_cache()
            rows.append(row)
    return rows

if __name__ == '__main__':
    print(json.dumps(benchmark_gpu(json.loads(sys.argv[1])), allow_nan=False))
