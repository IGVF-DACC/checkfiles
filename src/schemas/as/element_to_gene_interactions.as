table element_to_gene_interactions
"BEDPE format for element to gene interactions"
(
string  chrom;        "Chromosome of enhancer element"
uint    chromStart;   "Start coordinate of enhancer element (0-based)"
uint    chromEnd;     "End coordinate of enhancer element"
string  chrom2;       "Chromosome of target gene transcription start site"
uint    chromStart2;  "Start coordinate of target gene transcription start site"
uint    chromEnd2;    "End coordinate of target gene transcription start site"
string  name;         "Name of enhancer-gene pair"
float   score;        "scE2G score for enhancer-gene pair"
char[1] strand1;      "Strand for enhancer element"
char[1] strand2;      "Strand for target gene"
)
