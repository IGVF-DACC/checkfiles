# How to Validate Files Locally

## Install Dependencies

1. Create a python environment and install dependencies from src/checkfiles/requirements.txt

    ```bash
    pip install -r src/checkfiles/requirements.txt
    ```

2. Download the tool validateFiles for validating bed files. The file is hosted here: <https://hgdownload.cse.ucsc.edu/admin/exe/>. Choose the correct folder for different operating system. For example, for macOS arm64, the file is in this folder: <https://hgdownload.cse.ucsc.edu/admin/exe/macOSX.arm64/>. Run the following command for downloading:

    ```bash
    rsync -aP rsync://hgdownload.soe.ucsc.edu/genome/admin/exe/macOSX.arm64/validateFiles /usr/local/bin/
    sudo chmod 755 /usr/local/bin/validateFiles
    ```

3. Install Rust and Cargo. Here is the command to install them on mac:

    ```bash
    curl https://sh.rustup.rs -sSf | sh
    ```

4. Install fastq_stats that calculates couple of fastq stats. Here is how to install it on Mac:

    ```bash
    git clone https://github.com/IGVF-DACC/fastq_stats.git
    cd fastq_stats
    cargo build --release
    sudo cp target/release/fastq_stats /usr/local/bin
    sudo chmod 755 /usr/local/bin/fastq_stats
    ```

5. Insall vcf assembly checker for checking vcf file. You can download the tool here accordingly: <https://github.com/EBIvariation/vcf-validator/releases>. Rename it to "vcf_assembly_checker". For macOS arm64, choose this file: <https://github.com/EBIvariation/vcf-validator/releases/download/v0.10.0/vcf_assembly_checker_macos_arm64>.  You may need to run those command inorder to use vcf assembly checker:

    ```bash
    chmod +x vcf_assembly_checker
    mv vcf_assembly_checker /usr/local/bin/
    brew install cmake boost
    ```

## Download the reference files for vcf file validation

You can run this command to download reference files:

```bash
python src/checkfiles/utils/download_ref_files.py
```

## Set environment variable IGVF_API_KEY and IGVF_SECRET_KEY if you want to validate seqspec file

```bash
export IGVF_API_KEY=XXXXXXXX
export IGVF_SECRET_KEY=XXXXXXXXXXXXXXXX
```

## Validate Files locally

Here are some examples to show you how to validate files locally.

Validating bam file:

```bash
python src/checkfiles/checkfiles_local.py --input_file_path src/tests/data/ENCFF206HGF.bam --file_format bam --md5sum 2d3b7df013d257c7052c084d93ff9026
```

Validating cram file:

```bash
python src/checkfiles/checkfiles_local.py --input_file_path src/tests/data/cram_valid.cram --file_format cram --reference_file_path src/checkfiles/supporting_files/grch38.fa --md5sum 2d3b7df013d257c7052c084d93ff9026
```

Validating bed, bigWig, bigInteract, bigBed and bedpe file:

```bash
python src/checkfiles/checkfiles_local.py --input_file_path src/tests/data/ENCFF597JNC.bed.gz --file_format bed --file_format_type bed3 --assembly GRCh38 --md5sum d1bae8af8fec54424cff157134652d26
```

Validating fasta file:

```bash
python src/checkfiles/checkfiles_local.py --input_file_path src/tests/data/ENCFF329FTG.fasta.gz --file_format fasta --md5sum c8c18396efe2a44e93f613d00c00823d
```

Validating fastq file:

```bash
python src/checkfiles/checkfiles_local.py --input_file_path src/tests/data/ENCFF594AYI.fastq.gz --file_format fastq --md5sum 3e814f4af7a4c13460584b26fbe32dc4
```

Validating tabular file (csv, tsv and txt):

```bash
python src/checkfiles/checkfiles_local.py --input_file_path src/tests/data/guide_rna_sequences_invalid.tsv.gz --file_format tsv --content_type "guide RNA sequences" --md5sum b8bfdca28ddbcc74128e3e3bb5febe24
```

Validating tabular file with your own schema file:

```bash
python src/checkfiles/checkfiles_local.py --input_file_path src/tests/data/guide_rna_sequences_invalid.tsv.gz --file_format tsv --content_type "guide RNA sequences" --md5sum b8bfdca28ddbcc74128e3e3bb5febe24 --tabular_file_schema_path src/schemas/table_schemas/your_own_schma.json
```

The script will scan max of 1000 tabular file errors as default. You can set the max number of errors if needed:

```bash
python src/checkfiles/checkfiles_local.py --input_file_path src/tests/data/guide_rna_sequences_invalid.tsv.gz --file_format tsv --content_type "guide RNA sequences" --md5sum b8bfdca28ddbcc74128e3e3bb5febe24 --max_tabular_file_errors 100
```

Validate vcf file:

```bash
python src/checkfiles/checkfiles_local.py --input_file_path src/tests/data/chry_variants_sample_valid.vcf.gz --file_format vcf --assembly GRCh38 --md5sum 99b7b2c055d087565970221a4845fa7f
```

Validate seqspec yaml file:

```bash
python src/checkfiles/checkfiles_local.py --input_file_path src/tests/data/seqspec_valid.yaml.gz --file_format yaml --content_type seqspec --md5sum f1859dd9d60554a8f8ab63b65b458267
```

Validate seqspec yaml file while skip onlist files check:

```bash
python src/checkfiles/checkfiles_local.py --input_file_path src/tests/data/seqspec_valid.yaml.gz --file_format yaml --content_type seqspec --onlist_skip --md5sum f1859dd9d60554a8f8ab63b65b458267
```
