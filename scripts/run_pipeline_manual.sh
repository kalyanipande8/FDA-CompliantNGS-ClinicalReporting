#!/usr/bin/env bash
# Runs the exact same per-sample commands that main.nf's Nextflow processes
# run (ALIGN_BWA, SORT_INDEX, CALL_VARIANTS, ANNOTATE_VARIANTS,
# CLINICAL_TIERING, GENERATE_REPORT), invoked directly with bash instead of
# through the Nextflow/HealthOmics engine, against synthetic tumor/normal
# FASTQ data. Only tumor samples are reported on (normal samples are aligned
# to demonstrate the paired tumor/normal design, mirroring real
# tumor-only-vs-paired somatic calling considerations), but variant calling
# and reporting run on the tumor BAMs in this simplified demonstration.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REF="data/reference/synthetic_reference.fasta"
GENE_MODEL="data/reference/gene_model.tsv"
MANIFEST="data/samples_manifest.tsv"

mkdir -p results/align results/variants results/annotation results/tiering results/reports

echo "== Indexing reference =="
bwa index "$REF"
samtools faidx "$REF"

while IFS=$'\t' read -r TUMOR NORMAL <&3; do
  TUMOR="${TUMOR%$'\r'}"
  NORMAL="${NORMAL%$'\r'}"
  for SAMPLE in "$TUMOR" "$NORMAL"; do
    R1="data/reads/${SAMPLE}_R1.fastq"
    R2="data/reads/${SAMPLE}_R2.fastq"
    BAM="results/align/${SAMPLE}.sorted.bam"

    echo "== [$SAMPLE] BWA-MEM alignment =="
    bwa mem -R "@RG\tID:${SAMPLE}\tSM:${SAMPLE}\tPL:ILLUMINA" "$REF" "$R1" "$R2" \
      | samtools sort -o "$BAM" -
    samtools index "$BAM"
    samtools flagstat "$BAM" > "results/align/${SAMPLE}.flagstat.txt"
  done

  echo "== [$TUMOR] variant calling (bcftools mpileup/call) =="
  BAM="results/align/${TUMOR}.sorted.bam"
  VCF="results/variants/${TUMOR}.vcf"
  bcftools mpileup -f "$REF" "$BAM" 2>/dev/null \
    | bcftools call -mv --ploidy 1 -Ov -o "$VCF" 2>/dev/null

  echo "== [$TUMOR] annotation =="
  ANNOT="results/annotation/${TUMOR}.annotated.tsv"
  python3 scripts/annotate_variants.py --vcf "$VCF" --gene-model "$GENE_MODEL" \
    --sample-id "$TUMOR" --out "$ANNOT"

  echo "== [$TUMOR] clinical tiering =="
  TIERED="results/tiering/${TUMOR}.tiered.tsv"
  python3 scripts/clinical_tiering.py --annotated "$ANNOT" --out "$TIERED"

  echo "== [$TUMOR] clinical report =="
  python3 scripts/generate_clinical_report.py --tiered "$TIERED" --sample-id "$TUMOR" \
    --flagstat "results/align/${TUMOR}.flagstat.txt" \
    --out "results/reports/${TUMOR}.report.md"
done 3< <(tail -n +2 "$MANIFEST")

echo "== Aggregating cohort summary =="
python3 scripts/aggregate_cohort_summary.py --tiering-dir results/tiering \
  --out results/reports/cohort_summary.md

echo "Pipeline complete. See results/reports/"
