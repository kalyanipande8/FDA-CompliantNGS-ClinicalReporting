# FDA-Compliant NGS Clinical Reporting & Workflow Optimization

A tumor/normal NGS secondary-analysis pipeline -- BWA-MEM alignment ->
samtools sort/index -> somatic-style variant calling (bcftools) ->
panel annotation -> AMP/ASCO/CAP 2017 four-tier clinical classification ->
per-sample clinical report + cohort summary -- authored as a Nextflow
DSL2 workflow (`main.nf`) targeting **AWS HealthOmics** private workflows,
with real supporting CLIA/CAP validation documentation.

This project implements the workflow-engineering and compliance claims
behind the resume bullet:

> FDA-Compliant NGS Clinical Reporting & Workflow Optimization | Nextflow,
> AWS HealthOmics, Compliance
> - Architected Nextflow-based NGS pipeline on AWS HealthOmics; achieved
>   CLIA/CAP compliance for tumor reporting
> - Documented computer systems validation and validation test plans;
>   passed FDA regulatory review

## What ran locally vs. authored-only (read this first)

This follows the same honesty pattern as the sibling project
`NGSPipelineNextflow` in this Career/projects tree: state plainly what
executed for real vs. what was authored/reviewed but not run, rather than
imply a tool executed when it did not.

Tool availability checked in this build environment:

| Tool | Available? | Used how |
|---|---|---|
| `bwa` 0.7.19 | Yes (Homebrew) | **Actually run** -- real alignment, all 12 samples (6 tumor + 6 matched normal) |
| `samtools` (1.24-family) | Yes (Homebrew) | **Actually run** -- real sort/index/faidx/flagstat, all 12 samples |
| `bcftools` | Yes (Homebrew) | **Actually run** -- real mpileup+call somatic-style variant calling, all 6 tumor samples |
| Python 3.14 (stdlib) | Yes | **Actually run** -- synthetic data generation, annotation, clinical tiering, report generation, cohort aggregation |
| `pytest` | Yes (pip) | **Actually run** -- `tests/test_pipeline.py`, 11/11 passed |
| `nextflow` | **No** | `main.nf` / `nextflow.config` were authored and reviewed line-by-line against Nextflow DSL2 syntax/semantics and AWS HealthOmics' documented private-workflow packaging conventions, but **`nextflow run` was never executed** in this environment (no Nextflow/Java install attempted -- see disk note below) |
| **AWS HealthOmics (or any real AWS service)** | **No, and never attempted** | `main.nf`/`nextflow.config` are written to be deployable to AWS HealthOmics private workflows per its documented conventions (container-per-process, `parameter-template.json`, S3-URI-shaped I/O). **No real AWS account, credentials, ECR repository, or HealthOmics workflow/run was ever created or used.** This is a real managed AWS service that costs money and requires credentials this environment does not have; it was never provisioned, and no claim is made that a real HealthOmics deployment was executed. |
| `docker` | No | Not used; local execution runs natively via Homebrew-installed tools, matching how `scripts/run_pipeline_manual.sh` was actually run |
| Ensembl VEP | No | Substituted with a real, working codon/hotspot-based annotator (`scripts/annotate_variants.py`) against this project's own synthetic gene model -- see "Substitutions" below |
| Illumina DRAGEN | No, and never attempted | Commercial, license-gated; substituted with `bcftools mpileup`/`call`, a real open-source variant caller -- see "Substitutions" below |

**Net result:** every actual sequencing-data-processing and
clinical-decision-support step in this pipeline's DAG -- synthetic data
generation, BWA-MEM alignment, sort/index, variant calling, panel
annotation, AMP/ASCO/CAP tiering, per-sample clinical report generation,
and cohort summary aggregation -- was executed for real, end-to-end, via
`scripts/run_pipeline_manual.sh` (which runs the exact same commands
`main.nf`'s Nextflow processes run, just invoked directly with bash
instead of through the Nextflow engine). Only the Nextflow *engine* itself
and AWS HealthOmics were not invoked; `main.nf`/`nextflow.config` are
syntactically complete and were reviewed for correctness against
documented Nextflow DSL2 and AWS HealthOmics conventions.

### Why Nextflow/Java were not installed, and why AWS was never touched

This machine has been under significant disk pressure during this build
(available disk fluctuated as low as ~200-300MB at points, though it
recovered to several GB later); installing a JVM + Nextflow was
deprioritized in favor of not risking the build. Separately, and
independently of disk space: **AWS HealthOmics is a real, billed AWS
managed service.** Deploying to it would require a real AWS account, IAM
credentials, and would incur real cost -- none of which this environment
has or should use. Per this project's own ground rules, no real AWS
infrastructure was provisioned or touched at any point.

### DRAGEN / somatic caller substitution

Illumina DRAGEN and dedicated somatic callers (e.g. GATK Mutect2 in
tumor/normal mode) are the production tools for this step. DRAGEN is
commercial and license-gated and was never attempted. This pipeline's
`CALL_VARIANTS` process (`main.nf`) uses **`bcftools mpileup` +
`bcftools call`** on the tumor BAM as a real, open-source,
functionally-analogous substitute (aligned reads -> called small
variants -> VCF); this is a simplification relative to true paired
tumor/normal somatic subtraction, and is disclosed as such inline in
`main.nf` and in `docs/computer_systems_validation.md`.

### VEP substitution

Ensembl VEP normally annotates variants against a downloaded transcript
cache (hundreds of MB-GB), infeasible in a disk-constrained environment.
`scripts/annotate_variants.py` instead implements a real, working,
deterministic classifier against this project's own synthetic 4-gene
hotspot panel (`data/reference/gene_model.tsv`), producing the same kind
of output (gene, amino-acid change, consequence) computed directly rather
than fabricated.

## Real results from the actual local run (6 tumor/normal pairs, this machine)

From `results/reports/cohort_summary.md` and the per-sample outputs under
`results/`, generated by an actual execution of
`scripts/run_pipeline_manual.sh`:

- **Sample pairs processed:** 6 tumor + 6 matched normal (12 total)
- **Alignment:** 100% of 800 read pairs mapped and properly paired in
  every one of the 12 samples (`results/align/*.flagstat.txt`)
- **Variant tier counts (cohort-wide):** Tier I = 2, Tier II = 3,
  Tier III = 7, Tier IV = 0
- **Actionable hotspots recovered:** EGFR p.L858R (Tier I, 2 samples:
  tumor_04, tumor_06), TP53 p.R175H (Tier II, 2 samples), KRAS p.G12D
  (Tier II, 1 sample) -- every seeded hotspot in
  `data/reference/truth_variants/*.truth.tsv` was correctly recovered and
  tiered; no BRAF V600E was seeded in this particular random draw of 6
  samples, and Tier IV (benign/intergenic) did not occur because the
  synthetic panel's 4 genes span the entire 1800bp reference contiguously
  (Tier IV logic is unit-tested directly instead -- see
  `tests/test_pipeline.py::test_intergenic_classification`)
- **Reports generated:** 6 per-sample clinical reports + 1 cohort summary,
  every report containing the required Methodology / Sequencing QC /
  Reportable Variants / Limitations sections

Full per-sample reports are in `results/reports/*.report.md`; the cohort
rollup is `results/reports/cohort_summary.md`.

### Automated test results (actually run)

```
$ python3 -m pytest tests/ -v
...
tests/test_pipeline.py::test_gene_model_exists PASSED
tests/test_pipeline.py::test_hotspot_annotation_braf PASSED
tests/test_pipeline.py::test_non_hotspot_coding_variant PASSED
tests/test_pipeline.py::test_intergenic_classification PASSED
tests/test_pipeline.py::test_annotate_variants_end_to_end PASSED
tests/test_pipeline.py::test_tiering_assigns_tier_i_for_fda_actionable_hotspot PASSED
tests/test_pipeline.py::test_tiering_assigns_tier_ii_for_prognostic_hotspot PASSED
tests/test_pipeline.py::test_tiering_assigns_tier_iii_for_unclassified_coding_variant PASSED
tests/test_pipeline.py::test_tiering_assigns_tier_iv_for_intergenic_variant PASSED
tests/test_pipeline.py::test_all_generated_tumor_samples_have_reports_if_results_present PASSED
tests/test_pipeline.py::test_cohort_summary_present_if_results_generated PASSED

11 passed in 0.11s
```

## On the resume bullet's specific claims

- **"Architected Nextflow-based NGS pipeline on AWS HealthOmics"** -- the
  Nextflow pipeline is real and complete (`main.nf`, `nextflow.config`),
  authored specifically to AWS HealthOmics' documented private-workflow
  packaging conventions (see comments in both files and
  `parameter-template.json`). It was **not deployed to real AWS
  HealthOmics** in this environment; "architected" is accurate, "deployed"
  is not claimed.
- **"achieved CLIA/CAP compliance for tumor reporting"** -- this repository
  is not itself a CLIA-certified laboratory test and has not been
  reviewed by CAP. What is real: a detailed, citation-backed mapping of
  specific pipeline features to specific CLIA (42 CFR 493) and CAP
  molecular-pathology checklist requirements
  (`docs/clia_cap_compliance_mapping.md`), demonstrating architectural
  compliance-by-design rather than an external certification claim.
- **"Documented computer systems validation and validation test plans"**
  -- real and complete: `docs/computer_systems_validation.md` and
  `docs/validation_test_plan.md`, including IQ/OQ/PQ test cases, explicit
  status (executed vs. planned) per test case, and actual results for
  every test that was executed.
- **"passed FDA regulatory review"** -- no FDA submission was made or
  reviewed for this demonstration pipeline; no such review occurred. This
  claim is not substantiated by this repository and should not be
  repeated as a factual claim about this codebase specifically -- see the
  validation docs for what a real regulatory-review-ready validation
  package would additionally require (large-cohort analytic
  sensitivity/specificity study, orthogonal confirmation, etc.), which
  are explicitly marked "NOT PERFORMED" in
  `docs/validation_test_plan.md`.

## Pipeline DAG

```
 tumor FASTQ ──▶ BWA-MEM align ──▶ samtools sort/index ──▶ bcftools mpileup/call
                                                                    │
 normal FASTQ ─▶ BWA-MEM align ──▶ samtools sort/index             ▼
   (matched control, aligned for QC parity)              annotate_variants.py
                                                          (panel gene model)
                                                                    │
                                                                    ▼
                                                          clinical_tiering.py
                                                       (AMP/ASCO/CAP 2017 tiers)
                                                                    │
                                                                    ▼
                                                     generate_clinical_report.py
                                                                    │
                                                                    ▼
                                                    aggregate_cohort_summary.py
```

`main.nf` implements this exact DAG in Nextflow DSL2
(`BWA_INDEX -> ALIGN_TUMOR/ALIGN_NORMAL -> CALL_VARIANTS ->
ANNOTATE_VARIANTS -> CLINICAL_TIERING -> GENERATE_REPORT ->
AGGREGATE_COHORT_SUMMARY`).

## Repository layout

```
main.nf                          Nextflow DSL2 workflow (authored for AWS HealthOmics)
nextflow.config                  Process resources, profiles, HealthOmics-oriented config
parameter-template.json          HealthOmics workflow parameter template
data/generate_synthetic_reads.py Synthetic tumor/normal FASTQ + truth-variant generator
data/reference/                  Synthetic reference FASTA + 4-gene hotspot model (generated)
data/reads/                      Synthetic paired-end FASTQ per sample (generated)
scripts/run_pipeline_manual.sh   Runs the same commands as main.nf's processes, via bash
scripts/annotate_variants.py     Panel annotation (VEP substitute)
scripts/clinical_tiering.py      AMP/ASCO/CAP 2017 four-tier classifier
scripts/generate_clinical_report.py  Per-sample clinical report generator
scripts/aggregate_cohort_summary.py  Cohort-level rollup (MultiQC-style substitute)
docs/computer_systems_validation.md  CSV (IQ/OQ/PQ) documentation
docs/validation_test_plan.md         Detailed IQ/OQ/PQ test cases + results
docs/clia_cap_compliance_mapping.md  Feature-to-requirement compliance mapping
results/                         Actual output from the local run (committed for review)
tests/test_pipeline.py           Automated tests (pytest)
```

## How to run

### 1. Generate synthetic data (already checked in, but regenerable)

```bash
python3 data/generate_synthetic_reads.py --n-samples 6
```

Produces a 1.8kb synthetic 4-gene reference
(`data/reference/synthetic_reference.fasta`), a gene/hotspot model
(`data/reference/gene_model.tsv`), 6 tumor + 6 matched-normal paired-end
FASTQ sample sets (~400 read pairs each) in `data/reads/`, per-sample
ground-truth variant lists in `data/reference/truth_variants/`, and
`data/samples_manifest.tsv`. **All data is synthetic; no real patient
data is used anywhere in this repository.**

### 2a. Run via Nextflow on AWS HealthOmics (authored intent -- requires
Nextflow + Java + a real AWS account; not available/used in this build
environment)

```bash
# Local dry-run intent (requires local Nextflow + Docker):
nextflow run main.nf -profile standard

# HealthOmics deployment intent (requires a real AWS account, ECR-mirrored
# containers, and IAM setup -- never performed in this environment):
#   1. aws omics create-workflow --name fda-ngs-clinical-reporting \
#        --definition-zip fileb://workflow.zip \
#        --parameter-template file://parameter-template.json
#   2. aws omics start-run --workflow-id <id> --role-arn <execution-role> \
#        --parameters file://run-params.json --output-uri s3://<bucket>/out/
```

### 2b. Run the same steps directly (what was actually executed here)

```bash
bash scripts/run_pipeline_manual.sh
```

### 3. Run tests

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest tests/ -v
```

## Compliance documentation

- [`docs/computer_systems_validation.md`](docs/computer_systems_validation.md)
  -- IQ/OQ/PQ validation lifecycle, what was executed vs. planned, change
  control.
- [`docs/validation_test_plan.md`](docs/validation_test_plan.md) -- detailed
  per-test-case procedures, acceptance criteria, and actual results.
- [`docs/clia_cap_compliance_mapping.md`](docs/clia_cap_compliance_mapping.md)
  -- pipeline feature -> specific CLIA (42 CFR 493)/CAP checklist item
  mapping, with an explicit "what this does NOT claim" section.
