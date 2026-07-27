# US-POINTER published evidence

## What is modeled

The repository versions aggregate estimates reported in Table 2 of the 2025
US-POINTER randomized clinical trial publication. The modeled outcomes are:

- Global cognitive function (primary outcome)
- Executive function (secondary outcome)
- Episodic memory (secondary outcome)
- Processing speed (secondary outcome)

For each outcome, the evidence table preserves the structured and self-guided
annual slopes, their 95% confidence intervals, the between-group difference,
the difference confidence interval, and the reported p-value when available.

The source table is `data/evidence/us_pointer_outcomes.csv`. Its loader validates
the expected columns, source URL, outcome uniqueness, numeric values, and
confidence-limit ordering.

## What the trial supports

Random assignment supports a causal comparison between the structured and
self-guided interventions in the enrolled population. The primary published
between-group difference was 0.029 standard deviations per year in global
cognitive function (95% CI, 0.008 to 0.050; p=0.008), favoring the structured
intervention.

## What it does not support

The published result does not establish that either intervention prevents
Alzheimer disease, provide an individual diagnosis or risk prediction, or
directly estimate how many dementia cases were prevented. Clinical significance
and durability require additional follow-up.

Participant-level US-POINTER records are not stored in this repository.

Source: Baker LD, Espeland MA, Whitmer RA, et al. *Structured vs Self-Guided
Multidomain Lifestyle Interventions for Global Cognitive Function: The US
POINTER Randomized Clinical Trial.* JAMA. 2025;334(8):681–691.
<https://jamanetwork.com/journals/jama/fullarticle/2837046>
