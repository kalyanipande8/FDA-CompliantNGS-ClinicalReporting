# Computer Systems Validation (CSV) -- FDA-Compliant NGS Clinical Reporting Pipeline

## 1. Purpose and Scope

This document describes the computer systems validation (CSV) approach for
the software components of this tumor NGS secondary-analysis and clinical
reporting pipeline, consistent with CLIA requirements for laboratory
computer systems (42 CFR 493.1200s, 493.1253) and CAP All Common (COM)
checklist requirements for laboratory information/computer system
validation (COM.40300 series), and informed by FDA's general
principles of software validation (FDA "General Principles of Software
Validation," 2002) as commonly applied in CLIA-lab CSV practice.

**System under validation:** the pipeline defined by `main.nf` +
`nextflow.config` (target deployment: AWS HealthOmics private workflow) and
its constituent scripts (`scripts/annotate_variants.py`,
`scripts/clinical_tiering.py`, `scripts/generate_clinical_report.py`,
`scripts/aggregate_cohort_summary.py`), together referred to as "the
System."

**Disclosure:** This CSV package was authored against this pipeline as a
demonstration/portfolio artifact. The IQ steps that require a real target
deployment platform (AWS HealthOmics with production IAM/ECR/S3
configuration) are documented as **planned IQ procedures, not executed
IQ results** -- no real AWS deployment was performed in this environment
(see README.md). The OQ/PQ steps that exercise the pipeline's own
scientific/software logic on synthetic data **were executed for real**,
locally, with real open-source bioinformatics tools, and their actual
output is captured in `results/` and referenced below.

## 2. Validation Lifecycle Model

This CSV follows the standard four-phase molecular-lab computer-system
validation model:

1. **Installation Qualification (IQ)** -- verify the System and its
   dependencies are correctly installed in the intended execution
   environment.
2. **Operational Qualification (OQ)** -- verify each System component
   performs its intended function correctly across defined inputs,
   including boundary/edge cases.
3. **Performance Qualification (PQ)** -- verify the System performs
   correctly under conditions representative of actual intended use
   (realistic sample cohort, full end-to-end run, acceptance criteria
   tied to clinical reportability).
4. **Ongoing/Periodic Revalidation** -- triggers and procedure for
   re-running IQ/OQ/PQ (or a documented subset) after any change to the
   System or its execution environment.

## 3. Installation Qualification (IQ)

### 3.1 Target environment: AWS HealthOmics private workflow (PLANNED -- not executed)

| IQ step | Expected evidence | Status |
|---|---|---|
| Workflow package (`main.nf`, `nextflow.config`, `parameter-template.json`, `scripts/`) uploaded and registered as an AWS HealthOmics private workflow | HealthOmics console/API `CreateWorkflow` response showing workflow ID and `READY` status | **Not executed** -- no AWS account/credentials in this build environment |
| All container images referenced by `main.nf` mirrored into a private ECR repository in the target account/region | ECR `DescribeImages` output for each of `bwa`, `bcftools`, `python:3.11-slim` images | **Not executed** |
| IAM execution role for the workflow has least-privilege access to the specific input/output S3 prefixes only | IAM policy document + `iam:SimulatePrincipalPolicy` test results | **Not executed** |
| Workflow run submitted successfully against a small test dataset staged in S3 | HealthOmics `GetRun` response showing `COMPLETED` status | **Not executed** |

### 3.2 Local development/authoring environment (EXECUTED)

| IQ step | Expected evidence | Status | Actual result |
|---|---|---|---|
| `bwa` installed and callable | `bwa` prints usage/version | Executed | `bwa` 0.7.19-r1273 present via Homebrew, confirmed via `bwa index`/`bwa mem` runs in `results/` |
| `samtools` installed and callable | `samtools --version` | Executed | `samtools` 1.24-family present via Homebrew, confirmed via real `sort`/`index`/`faidx`/`flagstat` invocations |
| `bcftools` installed and callable | `bcftools --version` | Executed | `bcftools` present via Homebrew, confirmed via real `mpileup`/`call` invocations |
| `python3` installed with only-stdlib scripts runnable | `python3 --version`; script exit code 0 | Executed | Python 3.14 present; all `scripts/*.py` ran successfully end-to-end (see `results/`) |
| `nextflow` / Java runtime | `nextflow -version` | **Not executed** | `nextflow` binary not installed in this build environment; `main.nf`/`nextflow.config` were authored and manually reviewed against Nextflow DSL2 syntax/semantics instead (see README.md) |

## 4. Operational Qualification (OQ) -- EXECUTED locally

OQ test cases exercise each pipeline component in isolation against
synthetic inputs with known expected outputs. See
`docs/validation_test_plan.md` for the full OQ test-case table and
`tests/test_pipeline.py` for the corresponding automated assertions.

Summary of what was executed (see README.md for full console output):

- **Alignment (BWA-MEM):** run against 6 synthetic tumor + 6 matched
  normal samples (12 total), 800 read pairs each. 100% of reads mapped and
  properly paired in every sample (`results/align/*.flagstat.txt`).
- **Variant calling (bcftools mpileup/call):** run against all 6 tumor
  BAMs; every seeded synthetic variant (hotspot + passenger) was
  recovered in the resulting VCFs.
- **Annotation (`scripts/annotate_variants.py`):** run against all 6
  tumor VCFs; every variant was correctly classified against the gene
  model (gene/intergenic, hotspot vs. non-hotspot), verified against
  the `data/reference/truth_variants/*.truth.tsv` ground truth.
- **Clinical tiering (`scripts/clinical_tiering.py`):** run against all
  6 annotated variant sets; hotspot variants were correctly assigned
  Tier I (BRAF V600E, EGFR L858R) or Tier II (KRAS G12D, TP53 R175H) per
  the AMP/ASCO/CAP 2017 framework, and non-hotspot/intergenic variants
  were correctly assigned Tier III.
- **Report generation:** run against all 6 tiered variant sets; each
  report included QC metrics, tiered variant tables, and the required
  limitations disclosure.
- **Automated regression tests:** `pytest tests/test_pipeline.py` -- see
  README.md for the actual pass/fail result and console output from this
  build.

## 5. Performance Qualification (PQ) -- EXECUTED on synthetic cohort; PARTIAL for clinical-use claims

| PQ criterion | Acceptance criteria | Executed against | Result |
|---|---|---|---|
| End-to-end pipeline completes without error across a full sample cohort | Exit code 0 for `scripts/run_pipeline_manual.sh` across all samples in `data/samples_manifest.tsv` | 6 tumor/normal sample pairs (synthetic) | See README.md for actual run log/timing |
| Every seeded hotspot variant is recovered and correctly tiered | 100% recovery + correct tier vs. `truth_variants/*.tsv` | 6 tumor samples (4 with a seeded hotspot) | See README.md for actual counts |
| Report includes all required clinical-report sections (methodology, QC, tiered variants, limitations) | Manual review of generated `results/reports/*.report.md` | All 6 tumor sample reports | Confirmed present in every generated report |
| Pipeline reproduces identical output on repeated runs with the same input (determinism) | Byte-identical (or semantically identical) tiering/annotation output across 2 runs | Re-run of `scripts/run_pipeline_manual.sh` | Deterministic given fixed synthetic input and fixed `random.seed()` in data generation; bcftools/bwa are themselves deterministic for a given input |
| Analytic sensitivity/specificity on a large, clinically representative validation cohort (real or realistic simulated tumor specimens spanning the assay's full intended variant spectrum, per CAP MOL.31025) | Statistically powered sensitivity/specificity/PPV/NPV estimates | **Not performed** | Out of scope for this demonstration pipeline; would require a dedicated validation study with orthogonal-method confirmation (e.g., ddPCR or Sanger) on a much larger, clinically sourced (or high-fidelity simulated) cohort -- explicitly disclosed as not done here |
| Full HealthOmics-deployed run under production-representative load/scale | Successful `COMPLETED` HealthOmics run(s) at representative sample throughput | **Not performed** | No real AWS deployment in this environment (see README.md) |

## 6. Change Control and Revalidation Triggers

Any of the following changes to the System require, at minimum, re-running
the affected OQ test cases from `docs/validation_test_plan.md`, and for
changes to the reference/gene model or tiering knowledge base, a full PQ
re-run:

- A change to `main.nf`, `nextflow.config`, or any `scripts/*.py` file.
- A change to a pinned container image tag/version referenced in `main.nf`.
- A change to `data/reference/gene_model.tsv` (e.g., adding/removing a
  hotspot or gene).
- A change to `scripts/clinical_tiering.py`'s `KNOWLEDGE_BASE` (e.g.,
  updating a tier assignment or evidence citation).
- A change to the target deployment environment (e.g., migrating from one
  AWS HealthOmics workflow version to another, or a Nextflow engine
  version bump).

All changes and their associated revalidation evidence should be recorded
in a change-control log (not included in this demonstration repository,
but would be a required artifact -- e.g. a CHANGELOG.md with linked
re-validation test run IDs -- in an actual CLIA-lab deployment).

## 7. Roles and Responsibilities (template)

In an actual CLIA-certified laboratory deployment, this section would name:
- the **Laboratory Director** (validation approval/sign-off authority),
- the **Technical Supervisor / Bioinformatics Lead** (executes and
  documents IQ/OQ/PQ),
- **Quality Assurance** (independent review of validation package before
  clinical go-live).

This demonstration repository does not have a real laboratory organization
behind it; this section is included to show the structure a real validation
package would require.
