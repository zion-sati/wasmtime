# Loop alignment on x86-64: Intel Core i5-12600K

Run on 2026-11-10 following `BENCHMARKING-LOOP-ALIGNMENT.md`, with wasmtime at f47550060 and Sightglass at
f0d2040.

## Machine

- Intel Core i5-12600K (6 P-cores with SMT, 4 E-cores). Runs pinned to the P-cores, logical CPUs 0 to 11
  (`taskset -c 0-11` and `--pin`); the E-cores (12 to 15) were left out.
- Ubuntu 26.04.1, Linux 7.0.0-42-generic.
- Frequency: `intel_pstate`, governor `powersave`, turbo on. Each benchmark's first two iterations per
  engine are dropped in the summaries (`summarize.py`) while the frequency ramps up; the Sightglass
  summaries (`loop-align-*.txt`) use every iteration.
- Nothing else ran beside the benchmarks.
- rustc 1.99.1.

## Correctness

The spec test suite fails the same 40 of 258 files with and without 64-byte alignment
(`wast-off.txt`, `wast-align.txt`): the lists are identical.

## Execution time

Sightglass `execution` phase, `cycles`, 20 iterations per engine over the 131 benchmarks of
`benchmarks/all.suite`.

| Run | Setting | Sightglass geomean (off / on) | Geomean of medians, off/on | Without noisy benchmarks | 2% or more faster / slower |
| --- | --- | --- | --- | --- | --- |
| 1 | 32 bytes, padding at most 16 | 24,906,822 / 24,825,697: no difference | 1.0028 | 1.0039 | 8 / 5 |
| 2 | 16 bytes, padding at most 8 | 24,719,290 / 24,802,743: no difference | 0.9917 | 1.0010 | 4 / 2 |

Above 1 means alignment is faster. `summary-32.txt` and `summary-16.txt` list the largest changes.

- Alignment helps a few loop-bound benchmarks a lot: `wat-bytecode-interp` runs 1.16x (32 bytes) and 1.15x
  (16 bytes) faster, `shootout-sieve` 1.11x (32 bytes), `libsodium-core4` and `libsodium-core6` 1.07x and
  1.06x (32 bytes).
- The largest slowdowns are `shootout-minicsv` (0.95 and 0.96) and `rust-wat` (0.97 and 0.98).
- Across the suite the effect is within noise: +0.4% at 32 bytes and +0.1% at 16 bytes without the noisy
  benchmarks.

**Noisy benchmarks.** `libsodium-box_easy2`, `libsodium-secretbox_easy2`, `libsodium-sodium_utils`,
`noop` (and `libsodium-auth3` in run 1) vary by more than 10% within one engine; `box_easy2` ranges from 8
million to 480 million cycles with alignment off as well as on. Their ratios (0.43 and 0.66 in run 2) say
nothing about alignment, so the geomean is also given without them.

**One aborted attempt.** The first attempt at run 1 stopped about a quarter of the way through: one
benchmark subprocess trapped (`unreachable` executed, the recorder's exit-status assertion failed). The
engine and benchmark were not recorded. Running every benchmark once per engine, and again with two pinned
iterations per engine, passed, and the rerun (the data here) completed without failures. Run 2 also
completed without failures.
