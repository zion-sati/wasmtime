#!/usr/bin/env python3
"""Summarise a Sightglass loop-alignment run: python3 summarize.py loop-align-32.csv [warm-up iterations]

For each benchmark, the first iterations of each engine are dropped (the frequency governor ramps up during
them), the median of the rest is taken, and the ratio off/on reported: above 1 means alignment is faster.
A benchmark whose samples vary by more than 10% (coefficient of variation) under either engine is listed as
noisy, and the geomean is also given without those.
"""

import csv
import math
import statistics
import sys
from collections import defaultdict

path = sys.argv[1]
warmup = int(sys.argv[2]) if len(sys.argv) > 2 else 2

samples = defaultdict(list)
for row in csv.DictReader(open(path)):
    if row["phase"] == "Execution" and row["event"] == "cycles":
        engine = "on" if "align-on" in row["engine"] else "off"
        samples[(row["wasm"], engine)].append(int(row["count"]))

ratios = {}
noisy = set()
for (wasm, engine), counts in samples.items():
    if engine != "off" or (wasm, "on") not in samples:
        continue
    off_counts, on_counts = counts[warmup:], samples[(wasm, "on")][warmup:]
    ratios[wasm] = statistics.median(off_counts) / statistics.median(on_counts)
    if any(statistics.stdev(c) / statistics.mean(c) > 0.10 for c in (off_counts, on_counts)):
        noisy.add(wasm)

def geomean(values):
    values = list(values)
    return math.exp(sum(math.log(v) for v in values) / len(values))


all_mean = geomean(ratios.values())
quiet_mean = geomean(r for w, r in ratios.items() if w not in noisy)
print(f"{path}: {len(ratios)} benchmarks, first {warmup} iterations of each engine dropped")
print(f"geomean off/on of medians: {all_mean:.4f} ({(all_mean - 1) * 100:+.2f}% for alignment)")
print(f"without the {len(noisy)} noisy benchmarks: {quiet_mean:.4f} ({(quiet_mean - 1) * 100:+.2f}%)")
print("noisy: " + ", ".join(sorted("/".join(w.split("/")[-2:]) for w in noisy)))
ratios = {w: r for w, r in ratios.items() if w not in noisy}
ordered = sorted(ratios.items(), key=lambda item: item[1])
for label, bound in (("at least 2% faster with alignment", 1.02), ("at least 2% slower with alignment", 1 / 1.02)):
    chosen = [w for w, r in ratios.items() if (r >= bound if bound > 1 else r <= bound)]
    print(f"{label}: {len(chosen)}")
print("slowest with alignment (noisy benchmarks left out):")
for wasm, ratio in ordered[:8]:
    print(f"  {ratio:.3f}  {wasm}")
print("fastest with alignment (noisy benchmarks left out):")
for wasm, ratio in reversed(ordered[-8:]):
    print(f"  {ratio:.3f}  {wasm}")
