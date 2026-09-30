# CLIA/CAP Compliance Mapping -- Tumor NGS Clinical Reporting Pipeline

This document maps specific technical features/controls of this pipeline
(`main.nf` + `scripts/*.py`) to specific CLIA (42 CFR Part 493, Subpart K:
Quality Systems for Nonwaived Testing) and CAP molecular-pathology/NGS
checklist requirements. It is written as this pipeline's own compliance
design document -- it does **not** claim any external accreditation, and no
real specimen or PHI data is involved anywhere in this repository (all
sequencing data is synthetic; see README.md).

The CAP citations below reference the CAP Molecular Pathology (MOL) and
All Common (COM) checklist item numbering as of the CAP 2023 edition, which
is the numbering scheme in wide molecular-lab use at the time of writing;
labs should always confirm current item numbers against their live CAP
checklist at time of use, since CAP revises checklist numbering periodically.

| Pipeline feature / control | Location | CLIA requirement | CAP checklist requirement | Why it satisfies the requirement |
|---|---|---|---|---|
| Deterministic, versioned workflow definition (`main.nf`, `nextflow.config`, pinned container image tags per process) | `main.nf` | 42 CFR 493.1253 -- Establishment and verification of performance specifications | MOL.35125 / COM.40000 (test system changes must be documented and reassessed) | A pinned, version-controlled workflow definition means the exact analytic method used for a given report can always be reconstructed and is not subject to silent drift (e.g. an untracked tool upgrade changing variant calls). Container images make hardware/OS/tool-version dependencies explicit and reproducible. |
| Reference genome/panel and gene model supplied as explicit, versioned pipeline inputs (not hardcoded) | `main.nf` params, `data/reference/` | 42 CFR 493.1251 -- Procedure manual | MOL.34985 (reference sequence version documented) | CLIA/CAP require the exact reference sequence version used for variant calling to be documented and traceable per run; parameterizing it (rather than embedding an undocumented default) makes this auditable per run. |
| Read-group tagging with sample ID (`@RG ID:/SM:`) at alignment (`ALIGN_TUMOR`/`ALIGN_NORMAL` processes) | `main.nf` | 42 CFR 493.1101 -- Specimen/sample identification | COM.01500 (specimen identification through all testing phases) | Read-group tagging binds every aligned read back to its originating sample through the entire downstream DAG (BAM -> VCF -> report), supporting chain-of-custody / sample-identity requirements through automated processing. |
| Alignment QC metrics captured and attached to the clinical report (`samtools flagstat`, `GENERATE_REPORT` process) | `main.nf`, `scripts/generate_clinical_report.py` | 42 CFR 493.1289 -- Test report; 493.1235 -- Facility QC requirements | MOL.32001 (minimum sequencing depth/QC metrics defined and monitored), COM.30000 (QC records) | CAP requires each reportable result be accompanied by objective evidence that assay QC metrics (e.g. mapping rate, depth) met the lab's pre-established acceptance criteria before results are released; capturing and displaying flagstat output in the report operationalizes this. |
| Deterministic, rule-based variant-to-tier classification citing AMP/ASCO/CAP 2017 four-tier system (`scripts/clinical_tiering.py`) | `scripts/clinical_tiering.py` | 42 CFR 493.1291 -- Test report content and interpretation | MOL.36600 / MOL.36960 (variant classification and reporting terminology) | CAP explicitly expects labs to classify and report somatic variants using a defined, published tiering system (AMP/ASCO/CAP 2017) rather than ad hoc judgment; encoding the tiers and their evidentiary basis in versioned code makes the classification logic auditable and consistent across runs/reviewers. |
| Explicit evidentiary citation per tier assignment (`KNOWLEDGE_BASE` dict with `evidence` field) | `scripts/clinical_tiering.py` | 42 CFR 493.1291(c) -- Report must include interpretation | MOL.36680 (evidence supporting variant classification documented) | Requirement that clinical significance calls be traceable to specific evidence (FDA approval status, guideline, literature) rather than an opaque score; this is implemented literally as a structured, reviewable evidence string attached to every Tier I/II call. |
| Clinical report includes explicit "Limitations" section disclosing assay scope, synthetic-data status, and non-clinical-use status | `scripts/generate_clinical_report.py` | 42 CFR 493.1291(f) -- Report must include information relevant to interpretation, including limitations | MOL.37200 (limitations of the assay are disclosed in the report) | CAP/CLIA require every molecular report to disclose the analytic and clinical limitations of the assay (e.g., panel scope, sensitivity); this pipeline's report generator always emits a limitations section rather than making it optional/omittable. |
| Cohort-level QC/variant-tier rollup (`AGGREGATE_COHORT_SUMMARY` process, `scripts/aggregate_cohort_summary.py`) | `main.nf`, `scripts/aggregate_cohort_summary.py` | 42 CFR 493.1289 -- Test records retention and review | COM.30450 (ongoing QC trend monitoring) | Supports the lab's ongoing/periodic QC review obligation (batch-to-batch trend monitoring of tier distribution and QC pass rate), rather than only per-specimen review. |
| Full pipeline execution trace/timeline (`trace`/`report`/`timeline` blocks) | `nextflow.config` | 42 CFR 493.1105 -- Retention requirements; 493.1235(c) -- Records of all quality control activities | COM.04250 (records of test performance retained per specimen) | Nextflow's execution trace/report/timeline provide a durable, per-run audit record of exactly which process ran on which inputs, with what resources and timing -- directly supporting the retained-test-record requirement. |
| Validation documentation as first-class deliverables (`docs/computer_systems_validation.md`, `docs/validation_test_plan.md`) | `docs/` | 42 CFR 493.1253 -- Establishment and verification of performance specifications (accuracy, precision, reportable range, reference range, analytic sensitivity/specificity) | MOL.30630 / MOL.31025 (validation of laboratory-developed NGS test prior to clinical use); COM.40300 (computer system validation) | CLIA requires each laboratory-developed test (including NGS pipelines) to be formally validated for these six performance characteristics before clinical use, and CAP additionally requires computer-system validation for any software used to generate or interpret results. This pipeline documents both explicitly rather than asserting compliance without evidence. |
| Deterministic tests (`tests/test_pipeline.py`) exercising annotation and tiering logic against known truth variants | `tests/test_pipeline.py`, `data/reference/truth_variants/` | 42 CFR 493.1253(b)(2) -- Accuracy verification against known results | MOL.31025 (accuracy verified against samples of known genotype) | CAP requires verification of pipeline accuracy against samples with known/expected results; the synthetic truth-variant files and pytest suite operationalize this on synthetic data, explicitly scoped as a pipeline-logic self-check rather than a full clinical validation study (see docs/validation_test_plan.md for what a full PQ study would additionally require). |

## What this mapping does NOT claim

- This repository has **not** been submitted to, or reviewed by, CAP or any
  CLIA-certified laboratory's compliance office, and is not itself a
  CLIA-certified test.
- No real patient specimens, PHI, or production sequencing data were used
  anywhere in this repository.
- The tiering knowledge base (`scripts/clinical_tiering.py`) covers four
  hand-curated, illustrative oncology hotspots (BRAF V600E, EGFR L858R,
  KRAS G12D, TP53 R175H); a real clinical assay would source its knowledge
  base from a maintained, versioned, and independently-validated resource
  (e.g. OncoKB, CIViC, or an internal curated variant database with its own
  change-control process), which this project explicitly does not attempt
  to replicate.
- AWS HealthOmics itself was never deployed to or run against in this
  environment (see README.md and main.nf); this mapping describes the
  pipeline's *design* intent for a HealthOmics-hosted deployment, not a
  validated production system.
