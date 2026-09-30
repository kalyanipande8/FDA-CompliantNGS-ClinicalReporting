#!/usr/bin/env python3
"""
Generate small synthetic tumor NGS data for the FDA-Compliant NGS Clinical
Reporting pipeline.

This is NOT real patient data. It builds:
  - a small synthetic reference FASTA covering a toy 4-gene "hotspot panel"
    modeled loosely on real cancer hotspots (BRAF V600E, EGFR L858R,
    KRAS G12D, TP53 R175H) so the clinical-tiering logic has something
    realistic to key off of
  - a gene model (TSV) mapping reference coordinates to gene / codon frame
  - paired-end FASTQ reads for N synthetic "tumor" samples and matched
    "normal" samples, each simulated by seeding a small reference with
    specific single-nucleotide substitutions (some at the hotspot codons,
    some passenger/background) and sampling read pairs with a low
    per-base simulated sequencing error rate.
  - a truth-variants file per sample (ground truth for validation).

Everything here uses only the Python standard library (random, textwrap).
"""
import argparse
import csv
import os
import random
import textwrap

random.seed(42)

BASES = "ACGT"

# Toy 4-gene panel. Each gene is a contiguous block of the synthetic
# reference. Coordinates are 0-based, half-open, within the synthetic
# reference (NOT real genome coordinates).
GENES = [
    # name, start, end, hotspot_offset (0-based within gene), hotspot_ref, hotspot_alt, hotspot_aa_change
    ("BRAF", 0, 450, 210, "T", "A", "p.V600E"),
    ("EGFR", 450, 900, 330, "T", "G", "p.L858R"),
    ("KRAS", 900, 1350, 45, "G", "A", "p.G12D"),
    ("TP53", 1350, 1800, 90, "G", "A", "p.R175H"),
]

REF_LEN = 1800


def make_reference():
    return "".join(random.choice(BASES) for _ in range(REF_LEN))


def write_fasta(path, name, seq, width=70):
    with open(path, "w") as fh:
        fh.write(f">{name}\n")
        for line in textwrap.wrap(seq, width):
            fh.write(line + "\n")


def write_gene_model(path):
    with open(path, "w") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["gene", "start", "end", "hotspot_pos", "hotspot_ref", "hotspot_alt", "hotspot_aa_change"])
        for gene, start, end, hs_off, hs_ref, hs_alt, hs_aa in GENES:
            w.writerow([gene, start, end, start + hs_off, hs_ref, hs_alt, hs_aa])


def revcomp(seq):
    comp = {"A": "T", "T": "A", "C": "G", "G": "C", "N": "N"}
    return "".join(comp[b] for b in reversed(seq))


def mutate(seq, pos, alt):
    return seq[:pos] + alt + seq[pos + 1:]


def simulate_reads(seq, n_pairs, read_len, insert_size, error_rate, rng):
    """Yield (r1_seq, r2_seq) pairs sampled from seq with sequencing error."""
    pairs = []
    max_start = len(seq) - insert_size
    for _ in range(n_pairs):
        start = rng.randint(0, max_start - 1)
        frag = seq[start:start + insert_size]
        r1 = frag[:read_len]
        r2 = revcomp(frag[-read_len:])
        r1 = "".join(
            (b if rng.random() > error_rate else rng.choice([x for x in BASES if x != b]))
            for b in r1
        )
        r2 = "".join(
            (b if rng.random() > error_rate else rng.choice([x for x in BASES if x != b]))
            for b in r2
        )
        pairs.append((r1, r2))
    return pairs


def write_fastq(path, pairs, prefix, read_index):
    with open(path, "w") as fh:
        for i, seq in pairs:
            qual = "I" * len(seq)
            fh.write(f"@{prefix}.{i}/{read_index}\n{seq}\n+\n{qual}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-samples", type=int, default=3)
    ap.add_argument("--n-pairs", type=int, default=400)
    ap.add_argument("--read-len", type=int, default=75)
    ap.add_argument("--insert-size", type=int, default=180)
    ap.add_argument("--error-rate", type=float, default=0.01)
    ap.add_argument("--out-dir", default=os.path.dirname(os.path.abspath(__file__)))
    args = ap.parse_args()

    ref_dir = os.path.join(args.out_dir, "reference")
    reads_dir = os.path.join(args.out_dir, "reads")
    truth_dir = os.path.join(ref_dir, "truth_variants")
    os.makedirs(ref_dir, exist_ok=True)
    os.makedirs(reads_dir, exist_ok=True)
    os.makedirs(truth_dir, exist_ok=True)

    ref_seq = make_reference()
    # Force each gene's hotspot position to its designated reference base so
    # the gene model's hotspot_ref annotations are always accurate.
    ref_list = list(ref_seq)
    for gene, start, end, hs_off, hs_ref, hs_alt, hs_aa in GENES:
        ref_list[start + hs_off] = hs_ref
    ref_seq = "".join(ref_list)
    write_fasta(os.path.join(ref_dir, "synthetic_reference.fasta"), "synthetic_panel_ref", ref_seq)
    write_gene_model(os.path.join(ref_dir, "gene_model.tsv"))

    manifest_rows = []
    for s in range(1, args.n_samples + 1):
        rng = random.Random(1000 + s)
        sample_id = f"tumor_{s:02d}"
        normal_id = f"normal_{s:02d}"

        # Tumor: mutate one randomly-chosen hotspot to ALT (simulating a
        # clinically actionable somatic variant), plus 1-2 random
        # low-relevance background passenger SNVs. Not every tumor sample
        # gets a hotspot hit, to mimic a mixed real-world cohort.
        tumor_seq = ref_seq
        truth = []
        if rng.random() < 0.75:
            gene, start, end, hs_off, hs_ref, hs_alt, hs_aa = rng.choice(GENES)
            pos = start + hs_off
            assert ref_seq[pos] == hs_ref, "gene model / reference mismatch"
            tumor_seq = mutate(tumor_seq, pos, hs_alt)
            truth.append((pos, hs_ref, hs_alt, gene, hs_aa, "hotspot"))

        # background passenger variants at non-hotspot, non-coding-critical
        # positions
        for _ in range(rng.randint(1, 2)):
            pos = rng.randint(0, REF_LEN - 1)
            if any(pos == t[0] for t in truth):
                continue
            ref_b = tumor_seq[pos]
            alt_b = rng.choice([b for b in BASES if b != ref_b])
            tumor_seq = mutate(tumor_seq, pos, alt_b)
            truth.append((pos, ref_b, alt_b, "intergenic", "-", "passenger"))

        # Normal (matched germline control): reference sequence, no somatic
        # variants introduced.
        normal_seq = ref_seq

        for label, seq in ((sample_id, tumor_seq), (normal_id, normal_seq)):
            pairs = simulate_reads(seq, args.n_pairs, args.read_len, args.insert_size, args.error_rate, rng)
            r1 = [(i, p[0]) for i, p in enumerate(pairs)]
            r2 = [(i, p[1]) for i, p in enumerate(pairs)]
            write_fastq(os.path.join(reads_dir, f"{label}_R1.fastq"), r1, label, 1)
            write_fastq(os.path.join(reads_dir, f"{label}_R2.fastq"), r2, label, 2)

        with open(os.path.join(truth_dir, f"{sample_id}.truth.tsv"), "w") as fh:
            w = csv.writer(fh, delimiter="\t")
            w.writerow(["pos_0based", "ref", "alt", "gene", "aa_change", "class"])
            for row in truth:
                w.writerow(row)

        manifest_rows.append((sample_id, normal_id))

    with open(os.path.join(args.out_dir, "samples_manifest.tsv"), "w") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["tumor_sample", "normal_sample"])
        for row in manifest_rows:
            w.writerow(row)

    print(f"Generated {args.n_samples} tumor/normal pairs under {reads_dir}")


if __name__ == "__main__":
    main()
