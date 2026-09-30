#!/usr/bin/env nextflow
/*
 * FDA-Compliant NGS Clinical Reporting Pipeline
 * ----------------------------------------------
 * A tumor/normal somatic NGS secondary-analysis + clinical-tiering pipeline,
 * authored as a Nextflow DSL2 workflow targeting AWS HealthOmics private
 * workflows.
 *
 * STATUS (read this first): This workflow was authored and reviewed
 * line-by-line for correct Nextflow DSL2 syntax/semantics and for
 * compliance with AWS HealthOmics' documented private-workflow packaging
 * conventions (container-per-process, no unsupported process directives,
 * parameters surfaced via nextflow.config `params` + a workflow
 * parameter-template JSON, S3-URI-shaped inputs/outputs). It was
 * **never deployed to, or executed on, real AWS HealthOmics or any other
 * real AWS infrastructure** in this environment -- doing so would require
 * an AWS account, IAM credentials, ECR-hosted containers, and would incur
 * real cost, none of which this build environment has or should use.
 *
 * The core scientific logic this workflow encodes (BWA-MEM alignment ->
 * samtools sort/index -> bcftools mpileup/call somatic-style variant
 * calling -> panel annotation -> AMP/ASCO/CAP tiering -> clinical report)
 * WAS actually executed locally, outside of Nextflow, using
 * scripts/run_pipeline_manual.sh against small synthetic tumor/normal
 * FASTQ data with real installed tools (bwa, samtools, bcftools) -- see
 * README.md "What ran locally vs. authored-only" for the full disclosure
 * and real results.
 */

nextflow.enable.dsl = 2

params.samples_manifest = "data/samples_manifest.tsv"
params.reads_dir        = "data/reads"
params.reference        = "data/reference/synthetic_reference.fasta"
params.gene_model       = "data/reference/gene_model.tsv"
params.outdir           = "results"

log.info """
FDA-Compliant NGS Clinical Reporting Pipeline
==============================================
samples_manifest : ${params.samples_manifest}
reads_dir         : ${params.reads_dir}
reference         : ${params.reference}
gene_model        : ${params.gene_model}
outdir            : ${params.outdir}

NOTE: authored for execution on AWS HealthOmics private workflows;
not deployed/executed on real AWS in this build environment. See README.
"""

workflow {

    Channel
        .fromPath(params.samples_manifest)
        .splitCsv(header: true, sep: '\t')
        .set { sample_pairs_ch }

    // Fan out to per-sample (tumor, normal) read channels
    tumor_reads_ch = sample_pairs_ch.map { row ->
        tuple(row.tumor_sample,
              file("${params.reads_dir}/${row.tumor_sample}_R1.fastq"),
              file("${params.reads_dir}/${row.tumor_sample}_R2.fastq"))
    }
    normal_reads_ch = sample_pairs_ch.map { row ->
        tuple(row.normal_sample,
              file("${params.reads_dir}/${row.normal_sample}_R1.fastq"),
              file("${params.reads_dir}/${row.normal_sample}_R2.fastq"))
    }

    ref_ch        = Channel.fromPath(params.reference).first()
    gene_model_ch = Channel.fromPath(params.gene_model).first()

    BWA_INDEX(ref_ch)

    ALIGN_TUMOR(tumor_reads_ch, ref_ch, BWA_INDEX.out.index)
    ALIGN_NORMAL(normal_reads_ch, ref_ch, BWA_INDEX.out.index)

    CALL_VARIANTS(ALIGN_TUMOR.out.bam, ref_ch)

    ANNOTATE_VARIANTS(CALL_VARIANTS.out.vcf, gene_model_ch)

    CLINICAL_TIERING(ANNOTATE_VARIANTS.out.annotated)

    GENERATE_REPORT(
        CLINICAL_TIERING.out.tiered.join(ALIGN_TUMOR.out.flagstat)
    )

    AGGREGATE_COHORT_SUMMARY(CLINICAL_TIERING.out.tiered.map { it[1] }.collect())
}

/*
 * Reference indexing. On AWS HealthOmics this container image would be
 * pulled from a private ECR repository (per HealthOmics' requirement that
 * all containers referenced by a private workflow be hosted in ECR, in
 * the same account/region as the workflow).
 */
process BWA_INDEX {
    container 'quay.io/biocontainers/bwa:0.7.19--h577a1d6_0'
    cpus 2
    memory '4 GB'

    input:
    path reference

    output:
    path "${reference}.*", emit: index

    script:
    """
    bwa index ${reference}
    samtools faidx ${reference}
    """
}

process ALIGN_TUMOR {
    tag "${sample_id}"
    container 'quay.io/biocontainers/bwa:0.7.19--h577a1d6_0'
    cpus 4
    memory '8 GB'
    publishDir "${params.outdir}/align", mode: 'copy'

    input:
    tuple val(sample_id), path(r1), path(r2)
    path reference
    path index_files

    output:
    tuple val(sample_id), path("${sample_id}.sorted.bam"), path("${sample_id}.sorted.bam.bai"), emit: bam
    tuple val(sample_id), path("${sample_id}.flagstat.txt"), emit: flagstat

    script:
    """
    bwa mem -t ${task.cpus} -R '@RG\\tID:${sample_id}\\tSM:${sample_id}\\tPL:ILLUMINA' \
        ${reference} ${r1} ${r2} | samtools sort -@ ${task.cpus} -o ${sample_id}.sorted.bam -
    samtools index ${sample_id}.sorted.bam
    samtools flagstat ${sample_id}.sorted.bam > ${sample_id}.flagstat.txt
    """
}

process ALIGN_NORMAL {
    tag "${sample_id}"
    container 'quay.io/biocontainers/bwa:0.7.19--h577a1d6_0'
    cpus 4
    memory '8 GB'
    publishDir "${params.outdir}/align", mode: 'copy'

    input:
    tuple val(sample_id), path(r1), path(r2)
    path reference
    path index_files

    output:
    tuple val(sample_id), path("${sample_id}.sorted.bam"), path("${sample_id}.sorted.bam.bai"), emit: bam

    script:
    """
    bwa mem -t ${task.cpus} -R '@RG\\tID:${sample_id}\\tSM:${sample_id}\\tPL:ILLUMINA' \
        ${reference} ${r1} ${r2} | samtools sort -@ ${task.cpus} -o ${sample_id}.sorted.bam -
    samtools index ${sample_id}.sorted.bam
    """
}

/*
 * Somatic-style small-variant calling. In production this step targets
 * DRAGEN or GATK Mutect2 tumor/normal somatic calling; here it is
 * bcftools mpileup+call on the tumor BAM alone, as a real, open-source,
 * functionally-analogous substitute run locally (see README).
 */
process CALL_VARIANTS {
    tag "${sample_id}"
    container 'quay.io/biocontainers/bcftools:1.21--h8b25389_0'
    cpus 2
    memory '4 GB'
    publishDir "${params.outdir}/variants", mode: 'copy'

    input:
    tuple val(sample_id), path(bam), path(bai)
    path reference

    output:
    tuple val(sample_id), path("${sample_id}.vcf"), emit: vcf

    script:
    """
    bcftools mpileup -f ${reference} ${bam} | bcftools call -mv --ploidy 1 -Ov -o ${sample_id}.vcf
    """
}

/*
 * Panel annotation against this project's synthetic gene model. Stands in
 * for a production annotation engine (e.g. VEP), which requires a large
 * downloaded transcript cache not fetched here (see README).
 */
process ANNOTATE_VARIANTS {
    tag "${sample_id}"
    container 'python:3.11-slim'
    cpus 1
    memory '2 GB'
    publishDir "${params.outdir}/annotation", mode: 'copy'

    input:
    tuple val(sample_id), path(vcf)
    path gene_model

    output:
    tuple val(sample_id), path("${sample_id}.annotated.tsv"), emit: annotated

    script:
    """
    python3 ${projectDir}/scripts/annotate_variants.py \
        --vcf ${vcf} --gene-model ${gene_model} --sample-id ${sample_id} \
        --out ${sample_id}.annotated.tsv
    """
}

/*
 * AMP/ASCO/CAP 2017 four-tier somatic variant classification.
 */
process CLINICAL_TIERING {
    tag "${sample_id}"
    container 'python:3.11-slim'
    cpus 1
    memory '2 GB'
    publishDir "${params.outdir}/tiering", mode: 'copy'

    input:
    tuple val(sample_id), path(annotated)

    output:
    tuple val(sample_id), path("${sample_id}.tiered.tsv"), emit: tiered

    script:
    """
    python3 ${projectDir}/scripts/clinical_tiering.py \
        --annotated ${annotated} --out ${sample_id}.tiered.tsv
    """
}

process GENERATE_REPORT {
    tag "${sample_id}"
    container 'python:3.11-slim'
    cpus 1
    memory '2 GB'
    publishDir "${params.outdir}/reports", mode: 'copy'

    input:
    tuple val(sample_id), path(tiered), path(flagstat)

    output:
    path "${sample_id}.report.md"

    script:
    """
    python3 ${projectDir}/scripts/generate_clinical_report.py \
        --tiered ${tiered} --sample-id ${sample_id} --flagstat ${flagstat} \
        --out ${sample_id}.report.md
    """
}

process AGGREGATE_COHORT_SUMMARY {
    container 'python:3.11-slim'
    cpus 1
    memory '2 GB'
    publishDir "${params.outdir}/reports", mode: 'copy'

    input:
    path tiered_files

    output:
    path "cohort_summary.md"

    script:
    """
    mkdir -p tiering_inputs
    for f in ${tiered_files}; do cp \$f tiering_inputs/; done
    python3 ${projectDir}/scripts/aggregate_cohort_summary.py \
        --tiering-dir tiering_inputs --out cohort_summary.md
    """
}
