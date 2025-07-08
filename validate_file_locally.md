# How to Validate Files Locally

To run the local validation you need to have a docker agent running in your system.

## Examples:

### Notes:

- Replace `[Absolute path to]` with the actual absolute path to your repository root directory, absolute path is required because the file is mounted into the dockder container.
- The script uses the `latest` Docker image tag by default.
- To use a specific version, add `--tag v25` (or your desired version) to the command.
- For seqspec validation with API access, both `--igvf-api-key` and `--igvf-secret-key` must be provided together.

Validating bam file:

```bash
./scripts/checkfiles_local.sh --input_file_path [Absolute path to]src/tests/data/ENCFF206HGF.bam --file_format bam --md5sum 2d3b7df013d257c7052c084d93ff9026
```

Validating cram file:

```bash
./scripts/checkfiles_local.sh --input_file_path [Absolute path to]src/tests/data/cram_valid.cram --file_format cram --reference_file_path src/checkfiles/supporting_files/grch38.fa --md5sum 2d3b7df013d257c7052c084d93ff9026
```

Validating bed, bigWig, bigInteract, bigBed and bedpe file:

```bash
./scripts/checkfiles_local.sh --input_file_path [Absolute path to]src/tests/data/ENCFF597JNC.bed.gz --file_format bed --file_format_type bed3 --assembly GRCh38 --md5sum d1bae8af8fec54424cff157134652d26
```

Validating fasta file:

```bash
./scripts/checkfiles_local.sh --input_file_path [Absolute path to]src/tests/data/ENCFF329FTG.fasta.gz --file_format fasta --md5sum c8c18396efe2a44e93f613d00c00823d
```

Validating fastq file:

```bash
./scripts/checkfiles_local.sh --input_file_path [Absolute path to]src/tests/data/ENCFF594AYI.fastq.gz --file_format fastq --md5sum 3e814f4af7a4c13460584b26fbe32dc4
```

Validating tabular file (csv, tsv and txt):

```bash
./scripts/checkfiles_local.sh --input_file_path [Absolute path to]src/tests/data/guide_rna_sequences_invalid.tsv.gz --file_format tsv --content_type "guide RNA sequences" --md5sum b8bfdca28ddbcc74128e3e3bb5febe24
```

Validating tabular file with your own schema file:

```bash
./scripts/checkfiles_local.sh --input_file_path [Absolute path to]src/tests/data/guide_rna_sequences_invalid.tsv.gz --file_format tsv --content_type "guide RNA sequences" --md5sum b8bfdca28ddbcc74128e3e3bb5febe24 --tabular_file_schema_path src/schemas/table_schemas/your_own_schma.json
```

The script will scan max of 1000 tabular file errors as default. You can set the max number of errors if needed:

```bash
./scripts/checkfiles_local.sh --input_file_path [Absolute path to]src/tests/data/guide_rna_sequences_invalid.tsv.gz --file_format tsv --content_type "guide RNA sequences" --md5sum b8bfdca28ddbcc74128e3e3bb5febe24 --max_tabular_file_errors 100
```

Validate vcf file:

```bash
./scripts/checkfiles_local.sh --input_file_path [Absolute path to]src/tests/data/chry_variants_sample_valid.vcf.gz --file_format vcf --assembly GRCh38 --md5sum 99b7b2c055d087565970221a4845fa7f
```

Validate seqspec yaml file:

```bash
./scripts/checkfiles_local.sh --input_file_path [Absolute path to]src/tests/data/seqspec_valid.yaml.gz --file_format yaml --content_type seqspec --md5sum f1859dd9d60554a8f8ab63b65b458267
```

Validate seqspec yaml file while skip onlist files check:

```bash
./scripts/checkfiles_local.sh --input_file_path [Absolute path to]src/tests/data/seqspec_valid.yaml.gz --file_format yaml --content_type seqspec --onlist_skip --md5sum f1859dd9d60554a8f8ab63b65b458267
```

Validate seqspec yaml file with IGVF API credentials (for accessing non-released files):

```bash
./scripts/checkfiles_local.sh --input_file_path [Absolute path to]src/tests/data/seqspec_valid.yaml.gz --file_format yaml --content_type seqspec --igvf-api-key "your-api-key" --igvf-secret-key "your-secret-key" --md5sum f1859dd9d60554a8f8ab63b65b458267
```


