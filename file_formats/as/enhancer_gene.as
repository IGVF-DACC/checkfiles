table enhancer_gene
"enhancer-gene links common file format"
(
string  chrom;		"Chromosome of the target of the perturbation (e.g., guideRNA, guideRNA pair). For guideRNA, use PAM. For element, use the element's chromosomal coordinates"
uint    chromStart;	"Zero-based starting position of the target of the perturbation (e.g., guideRNA, guideRNA pair). As with BED format, the start position in each BEDPE feature is therefore interpreted to be 1 greater than the start position listed in the feature. For guideRNA, use PAM. For guideRNA, use PAM. For element, use the element's chromosomal coordinates"
uint    chromEnd;	"One-based ending position of the target of the tested perturbation (e.g., guideRNA, guideRNA pair). For guideRNA, use PAM. For guideRNA, use PAM. For element, use the element's chromosomal coordinates"
string  name;		"gene|PerturbationTargetID. For non-expression screens, gene is 'NA'. For guide files, PerturbationTargetID is the guide's PAM in standard bed format. For negative controls (safes or non- targeting), gene is 'NA'. For safe-targeting controls, PerturbationTargetID is its PAM. For non-targeting controls, PerturbationTargetID is NT_n, where n is the unique identifying number for that sgRNA. For the element-level file format, the PerturbationTargetID is the element's chromosomal coordinates. Names must be unique"
float   EffectSize; "Effect size can be determined according to the data depositor's preference. The effect sizes can be across replicates or within replicate. Enhancers (positive regulators) of the measured gene's expression should have a positive effect size. Repressors (negative regulators) of the measured gene's expression should have a negative effect size. This may require additional formatting of the EffectSize column"
uint    SeqCounts;  "Sequencing counts associated with the guide for a collected population"
char[1] strandPerturbationTarget;  "Strand of perturbation target [+,-,.]; For guideRNA, this is the strand of the guideRNA. For element, use the element's strand. if strandedness is unclear or unnecessary, use '.' for the strand"
string  PerturbationTargetID;  "See name column for details on defining PerturbationTargetID"
string  chrTSS;  "Chromosome of the TSS of the tested/measured gene TSS. 'NA' for screens that measure phenotypes other than gene expression"
string  startTSS;  "Zero-based starting position of the tested/measured TSS. As with BED format, the start position in each BEDPE feature is therefore interpreted to be 1 greater than the start position listed in the feature. 'NA' for screens that measure phenotypes other than gene expression"
string  endTSS;  "One-based ending position of the tested/measured gene TSS. 'NA' for screens that measure phenotypes other than gene expression"
string  strandGene;  "Strand of gene TSS [+,-,.]. 'NA' for screens that measure phenotypes other than gene expression; if strandedness is unclear or unnecessary, use '.' for the strand"
string  EffectSize95ConfidenceIntervalLow;  "Lower bound of 95% confidence interval of effect size. 'NA' for screens that measure phenotypes other than gene expression"
string  EffectSize95ConfidenceIntervalHigh;  "Upper bound of 95% confidence interval of effect size. 'NA' for screens that measure phenotypes other than gene expression"
string  measuredGeneSymbol;  "HGNC Gene Symbol of target measured gene. 'NA' for screens that measure phenotypes other than gene expression"
string  measuredEnsemblID;  "Ensembl Gene ID. 'NA' for screens that measure phenotypes other than gene expression"
string  guideSpacerSeq;  "For element-level files, this is a semicolon separated list of gRNA protospacer sequences assigned to this connection, as applicable. 'NA' if not provided in element-level files. For single guides, there is only one protospacer sequence"
string  guideSeq;  "The gRNA sequence targeting the protospacer, as synthesized -- i.e. with the 'default' 5' G appended ONLY if it was included in the synthesis design. If no 5' G was appended to each guide, the value here is identical to the guideSpacerSeq column. For element-level files, this is a semicolon separated list of such gRNA sequences targeting the element. 'NA' if not provided in element-level files"
string  guideType;  "A qualitative classifier for the type of guide. Must be either 'negative_control' or 'targeting'"
enum('TRUE','FALSE')    Significant;  "'TRUE' or 'FALSE', depending on whether the connection was called significant in the original publication, or by the analysis method used"
string  pValue;  "Nominal p-value from the test"
string  pValueAdjusted;  "The multiple hypothesis adjusted p-value used to determine significance"
string  PowerAtEffectSize10;  "Power to detect 10% decrease in gene expression. 'NA' if not provided"
string  PowerAtEffectSize25;  "Power to detect 25% decrease in gene expression. 'NA' if not provided"
string  PowerAtEffectSize50;  "Power to detect 50% decrease in gene expression. 'NA' if not provided"
string  ValidConnection;  "'TRUE' for valid E-P connections. If not true, directly provide an invalidating reason for connections that should be removed -- for instance because they are in the promoter of the tested gene, or are an element in the gene body of the tested gene (in a KRAB-dCas9 experiment). 'NA' can also be provided, in which case no interpretation should be made using this column"
string  Notes;  "Free text; 'NA' if no notes"
)