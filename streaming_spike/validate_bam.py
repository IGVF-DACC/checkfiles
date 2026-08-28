"""Bucket 2 PoC: validate a bam by streaming from S3 via htslib's own range requests.

Mirrors the logic of `bam_pysam_check` in src/checkfiles/checkfiles.py, but takes an
s3:// (or https://) URL instead of a mounted local path. Nothing is downloaded to disk;
htslib fetches byte ranges over the network.

Returns a list of error strings ([] = valid).
"""
import pysam

# from src/checkfiles/constants.py NO_SQ_HEADER_BAM_CONTENT_TYPES
NO_SQ_HEADER_BAM_CONTENT_TYPES = ['subreads']


def validate_bam(url, content_type=None,
                 no_sq_header_bam_content_types=NO_SQ_HEADER_BAM_CONTENT_TYPES):
    errors = []
    info = {}
    try:
        if content_type not in no_sq_header_bam_content_types:
            pysam.quickcheck(url)
        result = pysam.stats(url)
        if 'SN\tis sorted:\t0' in result:
            return ['the bam file is not sorted'], info
        with pysam.AlignmentFile(url, 'rb', check_sq=False) as samfile:
            if not samfile.header:
                return ['the bam file has invalid header'], info
            info['read_count'] = samfile.count(until_eof=True)
    except pysam.utils.SamtoolsError as e:
        return [f'file is not valid bam file by SamtoolsError: {e}'], info
    except (OSError, ValueError) as e:
        # non-bam content / unreadable object surfaces here rather than as SamtoolsError
        return [f'could not read as bam: {type(e).__name__}: {e}'], info
    return errors, info


if __name__ == '__main__':
    import sys, time
    cases = [
        ('GOOD  bam 4.5MB  IGVFFI3323DCKT',
         's3://igvf-public/2026/06/10/155918fc-8dc2-4f25-8c1e-9d3fdfb07bc9/IGVFFI3323DCKT.bam',
         'alignments'),
        ('BAD   tsv.gz posing as bam IGVFFI3093TLUQ',
         's3://igvf-public/2025/04/21/a46d5d2d-f325-401d-afe4-3139e3cd9765/IGVFFI3093TLUQ.tsv.gz',
         'alignments'),
        ('BAD   bigWig posing as bam IGVFFI4381NFYZ',
         's3://igvf-public/2026/05/07/fac6e773-ae1c-487a-ae9d-c5af72c91046/IGVFFI4381NFYZ.bigWig',
         'alignments'),
        ('BAD   nonexistent key',
         's3://igvf-public/2026/06/10/155918fc-8dc2-4f25-8c1e-9d3fdfb07bc9/NOSUCHFILE.bam',
         'alignments'),
    ]
    for label, url, ct in cases:
        t0 = time.time()
        errs, info = validate_bam(url, ct)
        print(f'{label}\n   -> errors={errs}\n      info={info}  ({time.time()-t0:.1f}s)')
