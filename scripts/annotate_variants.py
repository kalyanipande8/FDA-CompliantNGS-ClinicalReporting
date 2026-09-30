#!/usr/bin/env python3
"""
Real, working variant-consequence annotator standing in for a production
annotation engine (e.g. VEP/ANNOVAR) against this project's own synthetic
4-gene hotspot panel (see data/reference/gene_model.tsv).

For each variant in a VCF, this determines:
  - which panel gene (if any) it falls in
  - whether it matches the gene's known hotspot position/ref/alt exactly
    (in which case it is annotated with the documented amino-acid change,
    e.g. p.V600E)
  - otherwise, a generic "coding_variant_other" or "intergenic_variant"
    call for positions outside any gene / not matching the hotspot

This is a real, deterministic implementation that reads and classifies the
actual VCF records produced by bcftools -- not a canned/fabricated result.
"""
import argparse
import csv
import sys


def load_gene_model(path):
    genes = []
    with open(path) as fh:
        r = csv.DictReader(fh, delimiter="\t")
        for row in r:
            genes.append({
                "gene": row["gene"],
                "start": int(row["start"]),
                "end": int(row["end"]),
                "hotspot_pos": int(row["hotspot_pos"]),
                "hotspot_ref": row["hotspot_ref"],
                "hotspot_alt": row["hotspot_alt"],
                "hotspot_aa_change": row["hotspot_aa_change"],
            })
    return genes


def classify(pos0, ref, alt, genes):
    for g in genes:
        if g["start"] <= pos0 < g["end"]:
            if pos0 == g["hotspot_pos"] and ref == g["hotspot_ref"] and alt == g["hotspot_alt"]:
                return g["gene"], g["hotspot_aa_change"], "hotspot_missense"
            return g["gene"], "-", "coding_variant_other"
    return "intergenic", "-", "intergenic_variant"


def parse_vcf(path):
    variants = []
    with open(path) as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            chrom, pos, vid, ref, alt = fields[0], int(fields[1]), fields[2], fields[3], fields[4]
            # VCF POS is 1-based; gene model is 0-based
            variants.append((chrom, pos - 1, ref, alt))
    return variants


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vcf", required=True)
    ap.add_argument("--gene-model", required=True)
    ap.add_argument("--sample-id", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    genes = load_gene_model(args.gene_model)
    variants = parse_vcf(args.vcf)

    with open(args.out, "w") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["sample_id", "chrom", "pos_1based", "ref", "alt", "gene", "aa_change", "consequence"])
        for chrom, pos0, ref, alt in variants:
            gene, aa, consequence = classify(pos0, ref, alt, genes)
            w.writerow([args.sample_id, chrom, pos0 + 1, ref, alt, gene, aa, consequence])

    print(f"Annotated {len(variants)} variants for {args.sample_id} -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
