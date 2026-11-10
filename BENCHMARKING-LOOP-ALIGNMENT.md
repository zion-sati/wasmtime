# Benchmarking loop alignment on x86-64

This branch is `loop-alignment` plus this file. It adds three Cranelift settings
that align the header of each innermost, non-cold loop:

- `loop_align_log2`: the alignment, as a power of two (0, the default, aligns nothing)
- `loop_align_max_padding`: the most bytes of padding inserted for one header
- `loop_align_max_insts`: the largest loop, in machine instructions, that is aligned (0 means no limit)

The goal is the data asked for on
[bytecodealliance/wasmtime#4883](https://github.com/bytecodealliance/wasmtime/issues/4883):
Sightglass runs over the whole suite, and code size. Code size is already
measured (below); what is missing is execution time on x86-64.

## Machine

- Intel Core i5-12600K, Linux, quiet: nothing else running, no builds beside the runs.
- Use P-cores only. On an i5-12600K they are usually logical CPUs 0 to 11;
  check with `lscpu --extended` (the E-cores have the lower `MAXMHZ`).
- Record the CPU model, kernel version and frequency governor with the results.

## Build

```sh
git clone --filter=blob:none -b loop-alignment-benchmarks https://github.com/zion-sati/wasmtime.git
cd wasmtime
git submodule update --init --filter=blob:none
cargo build --release -p wasmtime-bench-api
cargo build --release --bin wasmtime
cd ..
git clone --filter=blob:none https://github.com/bytecodealliance/sightglass.git
cd sightglass
cargo build --release
```

## Correctness with alignment forced on

Run the spec test suite with and without 64-byte alignment and compare the
failing files. The lists must be identical (some files fail in both because
this invocation does not enable every proposal).

```sh
W=../wasmtime/target/release/wasmtime
for f in ../wasmtime/tests/spec_testsuite/*.wast; do $W wast "$f" >/dev/null 2>&1 || echo "$f"; done > wast-off.txt
for f in ../wasmtime/tests/spec_testsuite/*.wast; do
  $W wast -C cranelift-loop_align_log2=6 -C cranelift-loop_align_max_padding=63 "$f" >/dev/null 2>&1 || echo "$f"
done > wast-align.txt
diff wast-off.txt wast-align.txt && echo identical
```

## Execution time

The same engine library under two names, so the only difference between the
two engines is the flags:

```sh
cp ../wasmtime/target/release/libwasmtime_bench_api.so /tmp/align-off.so
cp ../wasmtime/target/release/libwasmtime_bench_api.so /tmp/align-on.so
```

Run 1, 32-byte alignment with at most 16 bytes of padding (LLVM's setting for
Arm's Neoverse and Cortex-X cores):

```sh
taskset -c 0-11 ./target/release/sightglass-cli benchmark --pin \
  --benchmark-phase execution -i 20 --show-insignificant \
  -e /tmp/align-off.so --engine-flags '-C cranelift-loop_align_log2=0' \
  -e /tmp/align-on.so  --engine-flags '-C cranelift-loop_align_log2=5 -C cranelift-loop_align_max_padding=16' \
  benchmarks/all.suite > loop-align-32.txt
mv sightglass-data.csv loop-align-32.csv
```

Run 2, 16-byte alignment with at most 8 bytes of padding (LLVM's setting for
Cortex-A72, close to its x86 default of 16 bytes):

```sh
taskset -c 0-11 ./target/release/sightglass-cli benchmark --pin \
  --benchmark-phase execution -i 20 --show-insignificant \
  -e /tmp/align-off.so --engine-flags '-C cranelift-loop_align_log2=0' \
  -e /tmp/align-on.so  --engine-flags '-C cranelift-loop_align_log2=4 -C cranelift-loop_align_max_padding=8' \
  benchmarks/all.suite > loop-align-16.txt
mv sightglass-data.csv loop-align-16.csv
```

Run them one at a time. If a benchmark fails to run, note it and continue.

## Results

Put `wast-off.txt`, `wast-align.txt`, the two `.txt` summaries, the two `.csv`
files and the machine details in `results/x86-64-i5-12600K/` on this branch, or
hand them back if you cannot push here.

## Already measured

Native code size over `benchmarks/all.suite` (the span of the function symbols
in each `.cwasm`, so section page padding is not counted), against alignment
off:

| Setting | aarch64 total | x86-64 total | worst module (aarch64 / x86-64) |
| --- | --- | --- | --- |
| 16 bytes, padding at most 8 | +0.29% | +0.17% | +1.07% / +0.49% |
| 32 bytes, padding at most 16 | +0.48% | +0.32% | +1.53% / +0.97% |
| 64 bytes, padding at most 63 | +3.33% | +2.80% | +9.17% / +7.96% |

On an Apple M1 Max, alignment makes loop timings stable across code placement
but does not make them faster: a trial-division loop that runs between 1.00 and
1.22 of its best time at 16 placements runs at about 1.21 at every aligned one.
