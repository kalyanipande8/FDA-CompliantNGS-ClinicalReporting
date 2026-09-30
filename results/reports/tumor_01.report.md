# Tumor NGS Clinical Report (SYNTHETIC DATA)

**Specimen ID (synthetic):** tumor_01

**Report generated:** 2026-09-30T12:44:32.555620+00:00

**Assay:** Synthetic 4-gene hotspot panel (BRAF, EGFR, KRAS, TP53) -- demonstration pipeline only; not a validated clinical assay; no real patient or specimen data was used.

## Methodology

- Alignment: BWA-MEM (real, executed locally on synthetic FASTQ)
- Sort/Index: samtools (real, executed locally)
- Variant calling: bcftools mpileup + call (real, executed locally)
- Annotation: scripts/annotate_variants.py against the panel's own gene model (real, executed locally; substitutes for a production annotation engine such as VEP)
- Clinical tiering: scripts/clinical_tiering.py per AMP/ASCO/CAP 2017 four-tier somatic variant classification (real, executed locally)

## Sequencing QC (samtools flagstat)

```
800 + 0 in total (QC-passed reads + QC-failed reads)
800 + 0 primary
0 + 0 secondary
0 + 0 supplementary
0 + 0 duplicates
0 + 0 primary duplicates
800 + 0 mapped (100.00% : N/A)
800 + 0 primary mapped (100.00% : N/A)
800 + 0 paired in sequencing
400 + 0 read1
400 + 0 read2
790 + 0 properly paired (98.75% : N/A)
800 + 0 with itself and mate mapped
0 + 0 singletons (0.00% : N/A)
0 + 0 with mate mapped to a different chr
0 + 0 with mate mapped to a different chr (mapQ>=5)
```

## Reportable Variants

### Tier I -- Variants of Strong Clinical Significance

_None detected._

### Tier II -- Variants of Potential Clinical Significance

_None detected._

### Tier III -- Variants of Unknown Clinical Significance

| Gene | AA Change | Position | Ref>Alt | Consequence | Evidence |
|---|---|---|---|---|---|
| TP53 | - | synthetic_panel_ref:1558 | T>A | coding_variant_other | Variant falls within a reportable gene region but does not match a curated actionable hotspot; insufficient evidence for clinical significance without orthogonal review. |

### Tier IV -- Benign or Likely Benign Variants

_None detected._

## Limitations

This report is generated from **synthetic** sequencing data on a small 4-gene demonstration panel for pipeline-validation purposes. It is not a clinical report, was not generated from a real patient specimen, and must not be used for any real diagnostic, treatment, or billing decision. See docs/clia_cap_compliance_mapping.md and docs/computer_systems_validation.md for how this pipeline's design maps to real CLIA/CAP validation requirements.
