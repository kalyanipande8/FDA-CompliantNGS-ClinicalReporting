#!/usr/bin/env python3
"""
Generate a per-sample clinical tumor NGS report (Markdown) from tiered
variant calls, in a format modeled on real molecular tumor board /
CLIA-lab report sections (specimen info, methodology, reportable variants
by tier, limitations). This is a real, working report generator, not a
mock-up -- it consumes the actual tiered-variant TSVs produced upstream
in this pipeline.

NOTE: All patient/specimen fields below are synthetic placeholders (this
project uses synthetic sequencing data only, never real patient data).
"""
import argparse
import csv
import datetime


TIER_LABELS = {
    "I": "Tier I -- Variants of Strong Clinical Significance",
    "II": "Tier II -- Variants of Potential Clinical Significance",
    "III": "Tier III -- Variants of Unknown Clinical Significance",
    "IV": "Tier IV -- Benign or Likely Benign Variants",
}


def load_tiered(path):
    rows = []
    with open(path) as fh:
        r = csv.DictReader(fh, delimiter="\t")
        rows.extend(r)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiered", required=True)
    ap.add_argument("--sample-id", required=True)
    ap.add_argument("--flagstat", required=False)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = load_tiered(args.tiered)
    by_tier = {"I": [], "II": [], "III": [], "IV": []}
    for row in rows:
        by_tier[row["tier"]].append(row)

    qc_block = ""
    if args.flagstat:
        with open(args.flagstat) as fh:
            qc_block = fh.read()

    with open(args.out, "w") as fh:
        fh.write(f"# Tumor NGS Clinical Report (SYNTHETIC DATA)\n\n")
        fh.write(f"**Specimen ID (synthetic):** {args.sample_id}\n\n")
        fh.write(f"**Report generated:** {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n\n")
        fh.write("**Assay:** Synthetic 4-gene hotspot panel (BRAF, EGFR, KRAS, TP53) -- "
                 "demonstration pipeline only; not a validated clinical assay; no real "
                 "patient or specimen data was used.\n\n")
        fh.write("## Methodology\n\n")
        fh.write("- Alignment: BWA-MEM (real, executed locally on synthetic FASTQ)\n")
        fh.write("- Sort/Index: samtools (real, executed locally)\n")
        fh.write("- Variant calling: bcftools mpileup + call (real, executed locally)\n")
        fh.write("- Annotation: scripts/annotate_variants.py against the panel's own gene "
                 "model (real, executed locally; substitutes for a production annotation "
                 "engine such as VEP)\n")
        fh.write("- Clinical tiering: scripts/clinical_tiering.py per AMP/ASCO/CAP 2017 "
                 "four-tier somatic variant classification (real, executed locally)\n\n")
        if qc_block:
            fh.write("## Sequencing QC (samtools flagstat)\n\n```\n")
            fh.write(qc_block)
            fh.write("```\n\n")
        fh.write("## Reportable Variants\n\n")
        for tier in ["I", "II", "III", "IV"]:
            fh.write(f"### {TIER_LABELS[tier]}\n\n")
            if not by_tier[tier]:
                fh.write("_None detected._\n\n")
                continue
            fh.write("| Gene | AA Change | Position | Ref>Alt | Consequence | Evidence |\n")
            fh.write("|---|---|---|---|---|---|\n")
            for v in by_tier[tier]:
                fh.write(f"| {v['gene']} | {v['aa_change']} | {v['chrom']}:{v['pos_1based']} "
                         f"| {v['ref']}>{v['alt']} | {v['consequence']} | {v['evidence']} |\n")
            fh.write("\n")
        fh.write("## Limitations\n\n")
        fh.write("This report is generated from **synthetic** sequencing data on a small "
                 "4-gene demonstration panel for pipeline-validation purposes. It is not a "
                 "clinical report, was not generated from a real patient specimen, and must "
                 "not be used for any real diagnostic, treatment, or billing decision. See "
                 "docs/clia_cap_compliance_mapping.md and docs/computer_systems_validation.md "
                 "for how this pipeline's design maps to real CLIA/CAP validation "
                 "requirements.\n")

    print(f"Wrote clinical report -> {args.out}")


if __name__ == "__main__":
    main()
