from pathlib import Path
import subprocess
import requests
import pysam
import argparse

FILE_URLS = {
    'GRCh38': 'https://api.data.igvf.org/reference-files/IGVFFI6815WBWB/@@download/IGVFFI6815WBWB.fasta.gz',
    'GRCm39': 'https://api.data.igvf.org/reference-files/IGVFFI9282QLXO/@@download/IGVFFI9282QLXO.fasta.gz',
}


def download_file(key, url, dir_path):
    '''
    Download the gz file from a URL, ungzip the file and save it to a path.
    The file name should be the key + '.fa'.
    url: URL to download the file from
    '''
    gz_path = dir_path / (key.lower() + '.fa.gz')
    # Download the file
    print(f'Downloading {key} fasta file to {gz_path}...')
    r = requests.get(url)
    r.raise_for_status()
    # Save the gz file
    with open(gz_path, 'wb') as f:
        f.write(r.content)
    # Ungzip the file
    subprocess.run(['gzip', '-d', gz_path])


def create_fai_file(fasta_path):
    '''
    Create a fasta index file for a fasta file.
    fasta_path: Path object to the fasta file
    '''
    print(f'Indexing {fasta_path}...')
    # add .fai to fasta_path
    fai_path = fasta_path.with_suffix('.fa.fai')
    if not fai_path.exists():
        pysam.faidx(str(fasta_path))


def main():
    parser = argparse.ArgumentParser(description='Download reference files for VCF validation')
    parser.add_argument('--local-dir', 
                       default='./src/checkfiles/supporting_files/',
                       help='Directory to store downloaded reference files (default: ./src/checkfiles/supporting_files/)')
    
    args = parser.parse_args()
    local_dir = Path(args.local_dir)
    
    # Create directory if it doesn't exist
    local_dir.mkdir(parents=True, exist_ok=True)
    
    for assembly, url in FILE_URLS.items():
        fasta_path = local_dir / (assembly.lower() + '.fa')
        if not fasta_path.exists():
            download_file(assembly, url, local_dir)
            create_fai_file(fasta_path)


if __name__ == '__main__':
    main()
