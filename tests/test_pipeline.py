"""
Real, executable tests for the pipeline's annotation, tiering, and report
generation logic (the parts of this pipeline that run outside the Nextflow
engine -- see README.md for what was/wasn't executed). Run with:

    python3 -m pytest tests/ -v
"""
import csv
import glob
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import annotate_variants  # noqa: E402
import clinical_tiering  # noqa: E402


GENE_MODEL = os.path.join(ROOT, "data", "reference", "gene_model.tsv")


def _write_vcf(tmpdir, records):
    path = os.path.join(tmpdir, "test.vcf")
    with open(path, "w") as fh:
        fh.write("##fileformat=VCFv4.2\n")
        fh.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
        for chrom, pos, ref, alt in records:
            fh.write(f"{chrom}\t{pos}\t.\t{ref}\t{alt}\t60\tPASS\t.\n")
    return path


def test_gene_model_exists():
    assert os.path.exists(GENE_MODEL), (
        "gene_model.tsv missing -- run data/generate_synthetic_reads.py first"
    )


def test_hotspot_annotation_braf():
    genes = annotate_variants.load_gene_model(GENE_MODEL)
    # BRAF hotspot: pos0=210 (1-based VCF pos = 211), ref T, alt A
    gene, aa, consequence = annotate_variants.classify(210, "T", "A", genes)
    assert gene == "BRAF"
    assert aa == "p.V600E"
    assert consequence == "hotspot_missense"


def test_non_hotspot_coding_variant():
    genes = annotate_variants.load_gene_model(GENE_MODEL)
    # Position within BRAF's span (0-450) but not the hotspot position/allele
    gene, aa, consequence = annotate_variants.classify(50, "A", "G", genes)
    assert gene == "BRAF"
    assert aa == "-"
    assert consequence == "coding_variant_other"


def test_intergenic_classification():
    genes = annotate_variants.load_gene_model(GENE_MODEL)
    # Position beyond all gene spans in the current 4-gene, 1800bp model
    gene, aa, consequence = annotate_variants.classify(5000, "C", "T", genes)
    assert gene == "intergenic"
    assert consequence == "intergenic_variant"


def test_annotate_variants_end_to_end(tmp_path):
    vcf = _write_vcf(str(tmp_path), [
        ("synthetic_panel_ref", 211, "T", "A"),   # BRAF hotspot, 1-based
        ("synthetic_panel_ref", 5001, "C", "T"),  # intergenic
    ])
    out = str(tmp_path / "annotated.tsv")
    annotate_variants_main = [
        sys.executable, os.path.join(ROOT, "scripts", "annotate_variants.py"),
        "--vcf", vcf, "--gene-model", GENE_MODEL, "--sample-id", "unit_test_sample",
        "--out", out,
    ]
    result = subprocess.run(annotate_variants_main, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    with open(out) as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    assert len(rows) == 2
    assert rows[0]["gene"] == "BRAF"
    assert rows[0]["aa_change"] == "p.V600E"
    assert rows[1]["gene"] == "intergenic"


def test_tiering_assigns_tier_i_for_fda_actionable_hotspot():
    tier, evidence = clinical_tiering.tier_for("BRAF", "p.V600E", "hotspot_missense")
    assert tier == "I"
    assert "FDA-approved" in evidence

    tier, evidence = clinical_tiering.tier_for("EGFR", "p.L858R", "hotspot_missense")
    assert tier == "I"


def test_tiering_assigns_tier_ii_for_prognostic_hotspot():
    tier, _ = clinical_tiering.tier_for("KRAS", "p.G12D", "hotspot_missense")
    assert tier == "II"

    tier, _ = clinical_tiering.tier_for("TP53", "p.R175H", "hotspot_missense")
    assert tier == "II"


def test_tiering_assigns_tier_iii_for_unclassified_coding_variant():
    tier, _ = clinical_tiering.tier_for("BRAF", "-", "coding_variant_other")
    assert tier == "III"


def test_tiering_assigns_tier_iv_for_intergenic_variant():
    tier, _ = clinical_tiering.tier_for("intergenic", "-", "intergenic_variant")
    assert tier == "IV"


def test_all_generated_tumor_samples_have_reports_if_results_present():
    """If results/ has already been generated (e.g. by run_pipeline_manual.sh),
    verify every tumor sample in the manifest has a corresponding report
    with the required sections. This is a soft integration check: it is
    skipped if results/ has not been generated yet."""
    reports_dir = os.path.join(ROOT, "results", "reports")
    if not os.path.isdir(reports_dir):
        return
    manifest = os.path.join(ROOT, "data", "samples_manifest.tsv")
    if not os.path.exists(manifest):
        return
    with open(manifest) as fh:
        tumor_samples = [row["tumor_sample"] for row in csv.DictReader(fh, delimiter="\t")]

    for sample in tumor_samples:
        report_path = os.path.join(reports_dir, f"{sample}.report.md")
        assert os.path.exists(report_path), f"missing report for {sample}"
        content = open(report_path).read()
        for heading in ["Methodology", "Sequencing QC", "Reportable Variants", "Limitations"]:
            assert heading in content, f"{sample} report missing '{heading}' section"


def test_cohort_summary_present_if_results_generated():
    summary = os.path.join(ROOT, "results", "reports", "cohort_summary.md")
    if not os.path.exists(summary):
        return
    content = open(summary).read()
    assert "Variant tier counts" in content
    assert "Per-sample tier breakdown" in content
