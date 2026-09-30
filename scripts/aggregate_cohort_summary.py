#!/usr/bin/env python3
"""Aggregate per-sample tiered-variant TSVs into one cohort-level summary
(a real, working stand-in for a MultiQC-style rollup, since multiqc itself
was not installed in this build environment -- see README)."""
import argparse
import csv
import glob
import os
from collections import Counter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiering-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    tier_counts = Counter()
    gene_counts = Counter()
    sample_rows = {}
    for path in sorted(glob.glob(os.path.join(args.tiering_dir, "*.tiered.tsv"))):
        sample = os.path.basename(path).replace(".tiered.tsv", "")
        with open(path) as fh:
            r = list(csv.DictReader(fh, delimiter="\t"))
        sample_rows[sample] = r
        for row in r:
            tier_counts[row["tier"]] += 1
            if row["gene"] != "intergenic":
                gene_counts[(row["gene"], row["aa_change"])] += 1

    with open(args.out, "w") as fh:
        fh.write("# Cohort Summary (synthetic tumor NGS demonstration cohort)\n\n")
        fh.write(f"Samples processed: {len(sample_rows)}\n\n")
        fh.write("## Variant tier counts (cohort-wide)\n\n")
        fh.write("| Tier | Count |\n|---|---|\n")
        for tier in ["I", "II", "III", "IV"]:
            fh.write(f"| {tier} | {tier_counts.get(tier, 0)} |\n")
        fh.write("\n## Actionable gene/hotspot hits\n\n")
        fh.write("| Gene | AA Change | Samples with this variant |\n|---|---|---|\n")
        for (gene, aa), n in sorted(gene_counts.items()):
            fh.write(f"| {gene} | {aa} | {n} |\n")
        fh.write("\n## Per-sample tier breakdown\n\n")
        fh.write("| Sample | Tier I | Tier II | Tier III | Tier IV |\n|---|---|---|---|---|\n")
        for sample, rows in sample_rows.items():
            c = Counter(row["tier"] for row in rows)
            fh.write(f"| {sample} | {c.get('I',0)} | {c.get('II',0)} | {c.get('III',0)} | {c.get('IV',0)} |\n")

    print(f"Wrote cohort summary -> {args.out}")


if __name__ == "__main__":
    main()
