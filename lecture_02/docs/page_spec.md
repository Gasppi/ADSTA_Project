# Case worker's page: requirements

Status (update when you change a part):
- [x] 1. User and task
- [x] 2. Flow and design guidelines
- [x] 3. Interface sheets (from `contracts.py` and `router.py`)
- [ ] 4. States of the screen
- [ ] 5. Acceptance criteria
- [ ] Open decisions (bottom of this file)

## 1. User and task

The user is a case worker. They decide on one credit application at a time and sign off on it.

The page has five jobs:
1. Take the two documents (payslip and debt register) and show what was read from them.
2. Let the case worker correct every value that was read, and add the rest.
3. Send the confirmed application to the backend.
4. Show the outcome with its reasons.
5. Say so when something could not be read or a service is down.

The page never decides. The backend decides (Model A and the rules). The page never calculates a
probability and never guesses a value.

## 2. Flow and design guidelines

### Flow

1. **Upload the two documents.** Payslip and debt register. Call `POST /extractions`.
2. **See what was read.** Show gross income, loss certificate and whether both documents name the
   same person. Also show the applicant's name and date of birth as read, for a cross-check.
3. **Correct it.** Every value that was read can be changed by the case worker.
4. **Enter the rest.** Age, dependants, open credit lines, real estate lines, the three late-payment
   counts, revolving utilisation and monthly debt obligations.
5. **Decide.** Call `POST /decisions` with the confirmed values and the `checkpoint` from step 1.
6. **Read the answer.** Outcome, reasons in words, the sentence written by Model C, and the decision
   number (`record_id`).

If the extraction service is down, the case worker can still enter every value by hand and decide.
In that case the page sends `extraction_checkpoint` as `null`.

### Rules that follow from the contract

- A value that could not be read is shown as "could not be read". It is sent as `null`. It is never
  filled with 0, `false` or a guess.
- Number fields start empty, never with a prefilled number, so an empty field cannot look like an answer.
- Income is sent as `Money` with currency `CHF` and the period shown on the screen.
- Reasons are shown in plain words:

| Reason code | Text on the page |
|---|---|
| `default_probability_above_threshold` | The estimated probability of default is above the bank's limit. |
| `loss_certificate_open` | The register shows an open loss certificate. |
| `loss_certificate_unknown` | The loss certificate could not be read. |
| `income_unknown` | The income could not be established. |

- The sentence in `wording` is labelled "Written by a model and not checked by a person." If
  `wording` is `null`, the page shows the reasons only and no sentence.
- If `same_applicant` is `false`, the page shows a warning that the documents name different
  people. The case worker still decides what to do (proposal).

### Design guidelines applied (Amershi et al., 2019)

| Guideline | On this page |
|---|---|
| G2: make clear how well the system can do what it can | The model-written sentence is labelled as unchecked. |
| G9: support efficient correction | The case worker can correct every value that Model B read. |
| G10: scope services when in doubt | A value that could not be read says so. The page never guesses it. |
| G11: make clear why the system did what it did | The outcome always comes with its reasons. |

## 3. Interface sheets

The page calls the backend at `BACKEND_URL`. Inside Compose that is `http://backend:8000`.
On a laptop it is `http://localhost:8000`.

### POST /extractions (page to backend, multipart)

| Field | Type | Meaning | When empty |
|---|---|---|---|
| `payslip` | file | the payslip document | required, else 422 |
| `debt_register` | file | the debt register extract | required, else 422 |

Answer 200, `ExtractionResult`. Every value is `null` when it could not be read.

| Field | Type | Meaning |
|---|---|---|
| `payslip.gross` | Money or null | gross salary, CHF, with its period |
| `debt_register.has_loss_certificate` | bool or null | open loss certificate on the register |
| `debt_register.applicant_name` | string or null | person the extract is made out to |
| `debt_register.date_of_birth` | date or null | applicant's date of birth |
| `same_applicant` | bool or null | both documents name the same person |
| `checkpoint` | string | the Model B (and revision) that read the documents |

Errors: 422 if a file is missing. 503 if the extraction service is down, with
`{"detail": "The Information Extraction Service is not available. Try again."}`.

### POST /decisions (page to backend, JSON)

Body: `{"entered": {...}, "extraction_checkpoint": string or null}`.
Send the `checkpoint` that the extraction returned. Send `null` if no documents were read.

| Field in `entered` | Type | Unit or range | When empty |
|---|---|---|---|
| `age` | integer | years, 18 to 120 | required |
| `dependants` | integer | persons, 0 or more | required |
| `open_credit_lines` | integer | count, 0 or more | required |
| `real_estate_lines` | integer | count, 0 or more | required |
| `late_30_59` | integer | payments 30 to 59 days late, 0 or more | required |
| `late_60_89` | integer | payments 60 to 89 days late, 0 or more | required |
| `late_90` | integer | payments 90 or more days late, 0 or more | required |
| `revolving_utilisation` | number | a share, 0.30 is 30 percent, 0 or more, no upper limit | required |
| `monthly_debt_obligations` | decimal string | CHF per month, 0 or more | required |
| `monthly_income` | Money or null | amount, currency `CHF`, period `monthly` or `annual` | `null` if nobody could read it. Never 0 |
| `has_loss_certificate` | bool or null | open loss certificate on the register | `null` if nobody could read it. Never false |

Money looks like `{"amount": "6000.00", "currency": "CHF", "period": "monthly"}`.

Answer 200, `DecisionResponse`:

| Field | Type | Meaning |
|---|---|---|
| `outcome` | `approved` or `refused` | decided by the backend rules, never by the page |
| `reasons` | list of reason codes | `default_probability_above_threshold`, `loss_certificate_open`, `loss_certificate_unknown`, `income_unknown` |
| `wording` | string or null | sentence written by Model C. `null` if Model C failed or timed out |
| `features` | object | the numbers the model used |
| `default_probability` | number or null | Model A's probability of default |
| `model_version` | string | which Model A decided |
| `record_id` | integer | id of the stored decision |

Errors: 422 if the body does not fit. Every POST creates a new record, so two clicks make two decisions.

### GET /health

Answer 200 `{"status": "ok"}`. Use it to check that the backend is up.

### GET /decisions/recent?limit=20 (optional for the page)

Answer 200, a list of stored decisions, newest first. Note: the stored record spells
`dependents`, the request spells `dependants`.

## Open decisions (to settle together, then write into the decision log)

- Does the page ask for utilisation as percent and divide by 100, or ask for the share?
- How long does the page wait for each call (timeout)? Model C can take 90 s to 3 min on a cold start.
- Does the Decide button disable itself while waiting, so a double click makes one decision?
- Does the page show recent decisions?
- Is age typed in, or calculated from the date of birth that was read?
- Confirm the two proposals: the warning when `same_applicant` is `false`, and manual entry when
  extraction is down.
