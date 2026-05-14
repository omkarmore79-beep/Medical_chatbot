# Dataset Expansion Plan

This plan defines the next external data sources to add, the exact fields to retain, and how each source should map into this project's retrieval pipeline.

Current status:
- Existing local datasets have already been cleaned/restructured.
- No new external datasets have been downloaded yet.
- This document is the implementation blueprint for the next expansion phase.

## Priority Order

1. `RxNorm / RxNav`
2. `DailyMed`
3. `openFDA drug label`
4. `gretelai/symptom_to_diagnosis`
5. `MIMIC-IV` (optional, advanced)

## Source Links

- RxNorm API: https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html
- DailyMed SPL downloads: https://dailymed.nlm.nih.gov/dailymed/spl-resources.cfm
- DailyMed API v2 `/spls`: https://dailymed.nlm.nih.gov/dailymed/webservices-help/v2/spls_api.cfm
- openFDA drug label API: https://open.fda.gov/apis/drug/label/how-to-use-the-endpoint/
- openFDA searchable fields: https://open.fda.gov/apis/drug/label/searchable-fields/
- Gretel symptom dataset: https://huggingface.co/datasets/gretelai/symptom_to_diagnosis
- MIMIC-IV: https://physionet.org/content/mimiciv/

## 1. Symptoms

### New source
- `gretelai/symptom_to_diagnosis`

### Why
- Adds natural-language patient phrasing.
- Improves routing for symptom questions like "burning while peeing", "tight chest", "feeling weak", "can't stop coughing".

### Local target files
- `knowledge_base/symptom_to_diagnosis_raw.jsonl`
- `knowledge_base/symptom_to_diagnosis_prepared.csv`

### Fields to keep
- `input_text`
- `output_text`

### Prepared schema
- `source`
- `input_text`
- `diagnosis`
- `normalized_input`
- `structured_text`

### Structured text format
```text
TYPE: SYMPTOM_NL
PATIENT_DESCRIPTION: {input_text}
POSSIBLE_CONDITION: {output_text}
SOURCE: gretelai/symptom_to_diagnosis
```

### Vectorstore
- `vectorstore_symptom_nl`

### Retrieval usage
- Query type: symptom triage, patient-described symptoms
- Merge with existing `vectorstore_symptoms`
- Prefer `vectorstore_symptom_nl` when query sounds like first-person free text

### Guardrail
- Use only for possible-condition guidance, not final diagnosis

## 2. Prescription / Medication Normalization

### New source
- `RxNorm / RxNav API`

### Why
- Standardized drug naming
- Brand/generic linking
- Better strength and dosage-form normalization
- Strong fit for prescription parsing and medicine-name normalization

### Useful RxNorm API functions
- `/rxcui?name=...`
- `/rxcui/{rxcui}/allProperties`
- `/rxcui/{rxcui}/allrelated`
- `/relatedndc`

The API docs describe these resources as part of the RxNorm API web service.

### Local target files
- `knowledge_base/rxnorm_concepts.csv`
- `knowledge_base/rxnorm_brand_generic_map.csv`

### Fields to keep
- `rxcui`
- `name`
- `tty`
- `ingredient`
- `dose_form`
- `strength`
- `brand_name`
- `generic_name`
- `ndc` if available

### Prepared schema
- `rxcui`
- `canonical_name`
- `term_type`
- `brand_name`
- `generic_name`
- `ingredients`
- `dose_form`
- `strength`
- `aliases`
- `structured_text`

### Structured text format
```text
TYPE: RXNORM_MEDICATION
CANONICAL_NAME: {canonical_name}
BRAND_NAME: {brand_name}
GENERIC_NAME: {generic_name}
INGREDIENTS: {ingredients}
DOSE_FORM: {dose_form}
STRENGTH: {strength}
RXCUI: {rxcui}
ALIASES: {aliases}
```

### Vectorstores
- `vectorstore_rxnorm`

### Retrieval usage
- Prescription OCR normalization
- Brand/generic lookup
- Strength-aware medicine retrieval
- Cross-check with local Indian brand mappings

## 3. Drug Labels and Safety

### New sources
- `DailyMed`
- `openFDA drug label`

### Why
- Better medicine safety answers than MedQuAD alone
- Gives indications, contraindications, warnings, adverse reactions, and sections of official labeling

### DailyMed notes
DailyMed offers:
- full SPL downloads
- indexing/mapping files
- API access through `/spls`

The API supports filters such as:
- `drug_name`
- `name_type`
- `labeler`
- `manufacturer`
- `ndc`
- `rxcui`

### openFDA notes
openFDA drug label endpoint:
- base endpoint: `https://api.fda.gov/drug/label.json`
- query syntax: `search=field:term`
- max `limit=1000`

### Local target files
- `knowledge_base/dailymed_labels_raw/`
- `knowledge_base/dailymed_prepared.csv`
- `knowledge_base/openfda_drug_label_prepared.csv`

### Fields to keep from DailyMed/openFDA
- product name
- brand name
- generic name
- manufacturer / labeler
- `indications_and_usage`
- `dosage_and_administration`
- `warnings`
- `boxed_warning`
- `contraindications`
- `adverse_reactions`
- `drug_interactions`
- `pregnancy`
- `lactation`
- `pediatric_use`
- `geriatric_use`
- `how_supplied`
- `rxcui` or `openfda.rxcui` if present
- `spl_set_id` or equivalent label id

### Prepared schema
- `drug_name`
- `brand_name`
- `generic_name`
- `manufacturer`
- `section_name`
- `section_text`
- `rxcui`
- `source`
- `structured_text`

### Structured text format
```text
TYPE: DRUG_LABEL
DRUG_NAME: {drug_name}
BRAND_NAME: {brand_name}
GENERIC_NAME: {generic_name}
SECTION: {section_name}
CONTENT: {section_text}
SOURCE: {source}
RXCUI: {rxcui}
```

### Vectorstores
- `vectorstore_drug_labels`
- `vectorstore_drug_safety`

### Retrieval usage
- Side effects
- Precautions
- Warnings
- Contraindications
- Pregnancy/breastfeeding guidance
- Dosing instructions

### Chunking rule
- Split label sections to 500-900 characters
- Keep one section per chunk
- Preserve section name in metadata and text

## 4. Drug Interactions

### Minimum approach
- Extract `drug_interactions` sections from DailyMed/openFDA

### Better approach
- Add DrugBank DDI data later if licensing/access is acceptable

### Local target files
- `knowledge_base/drug_interactions_prepared.csv`

### Fields to keep
- `drug_name`
- `generic_name`
- `interacting_drug`
- `interaction_severity` if available
- `interaction_text`
- `source`

### Structured text format
```text
TYPE: DRUG_INTERACTION
DRUG_NAME: {drug_name}
GENERIC_NAME: {generic_name}
INTERACTING_DRUG: {interacting_drug}
SEVERITY: {interaction_severity}
DETAILS: {interaction_text}
SOURCE: {source}
```

### Vectorstore
- `vectorstore_interactions`

### Retrieval usage
- "Does X interact with Y?"
- "Can I take these together?"

### Retrieval rule
- Interaction questions should search this store first, before general drug descriptions

## 5. Lab Reports

### Optional advanced source
- `MIMIC-IV`

### Why
- Real-world lab item names
- Units
- Common aliases
- Realistic clinical measurement naming

### Relevant MIMIC-IV tables
- `hosp/labevents`
- `hosp/d_labitems`
- optional later: `prescriptions`

PhysioNet describes the `hosp` module as containing laboratory measurements in `labevents` and `d_labitems`.

### Local target files
- `knowledge_base/mimic_lab_items.csv`
- `knowledge_base/lab_reference_aliases.csv`

### Fields to keep
- `itemid`
- `label`
- `fluid`
- `category`
- `loinc_code` if present
- `valueuom`

### Prepared schema
- `lab_key`
- `display_name`
- `aliases`
- `unit`
- `category`
- `loinc_code`
- `structured_text`

### Structured text format
```text
TYPE: LAB_TEST
DISPLAY_NAME: {display_name}
ALIASES: {aliases}
UNIT: {unit}
CATEGORY: {category}
LOINC: {loinc_code}
```

### Vectorstore
- `vectorstore_lab_refs`

### Retrieval usage
- Lab-test name normalization
- OCR alias recognition
- Unit-aware parser support

### Important note
- Do not use MIMIC-IV to answer general medical questions directly.
- Use it to normalize lab names, aliases, and units.

## Proposed New Retrieval Layout

- `vectorstore_symptoms`
  - curated structured symptom-disease rows
- `vectorstore_symptom_nl`
  - patient-style symptom descriptions
- `vectorstore_medqa`
  - general medical QA
- `vectorstore_rxnorm`
  - medication normalization
- `vectorstore_drug_labels`
  - indications, warnings, contraindications
- `vectorstore_interactions`
  - drug-drug interactions
- `vectorstore_indian_medicine`
  - India-specific brands and local medicine info
- `vectorstore_lab_refs`
  - lab test aliases and units

## Routing Rules To Implement

### Symptoms
- Search `vectorstore_symptom_nl`
- Then `vectorstore_symptoms`
- Then `vectorstore_medqa` only as fallback

### Medicine information
- Search `vectorstore_rxnorm`
- Then `vectorstore_indian_medicine`
- Then `vectorstore_drug_labels`

### Interaction questions
- Search `vectorstore_interactions` first
- Then `vectorstore_drug_labels`

### Prescription OCR
- Normalize brand/generic/strength with `vectorstore_rxnorm` and local Indian brand data
- Then answer with `vectorstore_indian_medicine` and `vectorstore_drug_labels`

### Lab questions
- For general test info: `vectorstore_lab_refs` + `vectorstore_medqa`
- For uploaded report interpretation: parser first, reference store second

## Practical Build Sequence

1. Add `gretelai/symptom_to_diagnosis`
2. Add RxNorm normalization store
3. Add DailyMed section extraction
4. Add openFDA label facts
5. Build interaction store from label sections
6. Add MIMIC-IV only if lab normalization still needs more coverage

## What Not To Do

- Do not embed full raw SPL XML documents directly
- Do not use MIMIC notes as general QA context
- Do not mix label sections and interactions into one undifferentiated vectorstore
- Do not replace local Indian brand mappings with U.S.-only sources

## Suggested Implementation Files

- `download_rxnorm.py`
- `prepare_rxnorm.py`
- `download_dailymed.py`
- `prepare_dailymed.py`
- `download_openfda_labels.py`
- `prepare_openfda_labels.py`
- `download_symptom_to_diagnosis.py`
- `prepare_symptom_to_diagnosis.py`
- `prepare_lab_references.py`

## Immediate Next Step

Start with:
- `gretelai/symptom_to_diagnosis`
- `RxNorm`
- `DailyMed`

These three additions will give the biggest improvement for:
- diverse symptom phrasing
- prescription normalization
- medicine safety and practical usage questions
