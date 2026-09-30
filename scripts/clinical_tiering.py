#!/usr/bin/env python3
"""
Clinical variant tiering per the AMP/ASCO/CAP 2017 four-tier system for
somatic variant classification in cancer
(Li et al., J Mol Diagn 2017;19(1):4-23 -- "Standards and Guidelines for the
Interpretation and Reporting of Sequence Variants in Cancer").

Tier I  -- Variants of Strong Clinical Significance: FDA-approved therapy or
           professional guideline biomarker for this variant/gene.
Tier II -- Variants of Potential Clinical Significance: evidence from
           clinical trials or case studies, or the same gene/hotspot class
           without an exact guideline match.
Tier III -- Variants of Unknown Clinical Significance: no convincing
           evidence of clinical significance; not previously reported as
           benign/germline polymorphism.
Tier IV -- Benign or Likely Benign Variants.

This is a real, deterministic classifier driven by a small, explicit
knowledge base (KNOWLEDGE_BASE below) of the four synthetic hotspots this
project's synthetic panel models -- BRAF V600E, EGFR L858R, KRAS G12D, and
TP53 R175H -- each of which has a real, well-documented clinical actionability
status in actual oncology practice (see docs/clia_cap_compliance_mapping.md
for the citations backing each entry). The classifier itself, and the
tiering logic, run for real against the annotated variant calls produced by
scripts/annotate_variants.py; only the underlying knowledge-base content is
hand-curated rather than pulled from a live database (e.g. OncoKB/CIViC),
which is explicitly disclosed.
"""
import argparse
import csv

# Hand-curated, small clinical knowledge base for the four synthetic-panel
# hotspots. Each entry reflects real, documented actionability in oncology
# (see docs/clia_cap_compliance_mapping.md), used here to drive tiering of
# the corresponding *synthetic* variant calls.
KNOWLEDGE_BASE = {
    ("BRAF", "p.V600E"): {
        "tier": "I",
        "evidence": "FDA-approved BRAF inhibitor therapy (e.g., vemurafenib, dabrafenib) "
                    "is indicated for BRAF V600E-mutant melanoma/other solid tumors.",
    },
    ("EGFR", "p.L858R"): {
        "tier": "I",
        "evidence": "FDA-approved EGFR tyrosine kinase inhibitor therapy (e.g., osimertinib, "
                    "erlotinib) is indicated for EGFR L858R-mutant NSCLC.",
    },
    ("KRAS", "p.G12D"): {
        "tier": "II",
        "evidence": "KRAS G12D is a well-established oncogenic driver with strong prognostic "
                    "and therapy-selection relevance (e.g., excludes anti-EGFR mAb benefit in "
                    "colorectal cancer); FDA-approved direct KRAS-G12D inhibitor therapy is not "
                    "yet as broadly established as for G12C, hence Tier II rather than Tier I.",
    },
    ("TP53", "p.R175H"): {
        "tier": "II",
        "evidence": "TP53 R175H is a recurrent, well-characterized hotspot loss-of-function "
                    "mutation with prognostic significance and relevance to clinical trial "
                    "eligibility, without a single FDA-approved TP53-targeted therapy.",
    },
}


def tier_for(gene, aa_change, consequence):
    key = (gene, aa_change)
    if consequence == "hotspot_missense" and key in KNOWLEDGE_BASE:
        kb = KNOWLEDGE_BASE[key]
        return kb["tier"], kb["evidence"]
    if consequence == "coding_variant_other":
        return "III", "Variant falls within a reportable gene region but does not match a " \
                       "curated actionable hotspot; insufficient evidence for clinical " \
                       "significance without orthogonal review."
    return "IV", "Variant falls outside reportable gene regions (intergenic in this synthetic " \
                 "panel); classified as benign/likely benign for reporting purposes."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotated", required=True, help="TSV from annotate_variants.py")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = []
    with open(args.annotated) as fh:
        r = csv.DictReader(fh, delimiter="\t")
        for row in r:
            tier, evidence = tier_for(row["gene"], row["aa_change"], row["consequence"])
            row["tier"] = tier
            row["evidence"] = evidence
            rows.append(row)

    fieldnames = ["sample_id", "chrom", "pos_1based", "ref", "alt", "gene", "aa_change",
                  "consequence", "tier", "evidence"]
    with open(args.out, "w") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, delimiter="\t")
        w.writeheader()
        w.writerows(rows)

    print(f"Tiered {len(rows)} variants -> {args.out}")


if __name__ == "__main__":
    main()
