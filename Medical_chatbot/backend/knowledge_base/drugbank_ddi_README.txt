DrugBank dedicated DDI data was not downloaded automatically.

Reason:
- DrugBank interaction data requires a DrugBank license and authenticated access.
- No DrugBank credentials were configured in this environment.

Expected next step:
1. Obtain DrugBank access or export a DrugBank interaction file.
2. Place the export in the knowledge_base folder.
3. Transform it into the schema shown in drugbank_ddi_template.csv.

Suggested columns:
- drug_name
- generic_name
- interacting_drug
- interaction_severity
- interaction_text
- source

If you later configure credentials, this script can be extended to fetch directly from the DrugBank API.
