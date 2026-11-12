# Case worker's page: requirements

Status (update when you change a part):
- [x] 1. User and task
- [x] 2. Flow and design guidelines
- [x] 3. Interface sheets (from `contracts.py` and `router.py`)
- [x] 4. States of the screen
- [x] 5. Acceptance criteria
- [ ] Open decisions (bottom of this file)

## 1. User and task

The user is a case worker. They decide on one credit application at a time and sign off on it.

The page has six jobs:
1. Take the two documents (payslip and debt register) and show what was read from them.
2. Let the case worker correct every value that was read, and add the rest.
3. Send the confirmed application to the backend.
4. Show the outcome with its reasons.
5. Say so when something could not be read or a service is down.
6. List the last 20 decisions.

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
7. **See the recent decisions.** A list of the last 20 decisions from `GET /decisions/recent`:
   decision number, time, outcome and reasons in words. It loads when the page opens and refreshes
   after each decision.

If the extraction service is down, the case worker can still enter every value by hand and decide.
In that case the page sends `extraction_checkpoint` as `null`.

### Rules that follow from the contract

- A value that could not be read is shown as "could not be read". It is sent as `null`. It is never
  filled with 0, `false` or a guess.
- Number fields start empty, never with a prefilled number, so an empty field cannot look like an answer.
- Income is sent as `Money` with currency `CHF` and the period shown on the screen.
- The loss certificate has three choices: none recorded (`false`), recorded (`true`) and could not be
  read (`null`). Nothing is preselected.
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

### GET /decisions/recent?limit=20 (page to backend)

Answer 200, a list of stored decisions. The page uses `id`, `created_at`, `outcome` and `reasons`.
The order of the list is not stated in the code, so the page sorts by `created_at`, newest first.
Note: the stored record spells `dependents`, the request spells `dependants`.

## 4. States of the screen

| State | When | What the page shows |
|---|---|---|
| Empty | at the start | No documents. Every number field is empty. Decide is disabled until every required field has a value. |
| Waiting | a call is running | "Reading the documents..." during `POST /extractions`. "Deciding..." during `POST /decisions`. |
| Not read | a value came back `null` | "could not be read" in a highlight, next to the field. The case worker can correct it or leave it. |
| Service down | a call failed | A message that says what failed and what happened. See the table below. |
| The answer | `POST /decisions` returned 200 | Outcome, reasons in words, the model-written sentence with its label, and the decision number. |

Every answer the page can get has its own sentence:

| What comes back | What the page shows |
|---|---|
| no answer in time, or no connection | "The backend does not answer. Nothing was decided." |
| 422 | "A field is missing or does not fit." The page names the field from `detail`. |
| 503 from `POST /extractions` | "The extraction service is not available. Try again, or enter the values by hand." |
| 500 or 503 from `POST /decisions` | "The backend failed. Nothing was decided." |
| 200 | The outcome, as in "The answer" above. |
| the recent list cannot be loaded | "The list of recent decisions could not be loaded." The rest of the page keeps working. |
| the recent list is empty | "No decisions yet." |

## 5. Acceptance criteria

| # | Requirement | How to check it |
|---|---|---|
| 1 | A case worker completes a decision through the page. | Upload both sample documents, correct if needed, fill the rest, press Decide. Outcome, reasons and a decision number appear. `GET /decisions/recent` lists that decision. |
| 2 | A value nobody could read says so. | With a document whose loss certificate cannot be read, or by choosing "could not be read", the page shows "could not be read". The answer's reasons contain `loss_certificate_unknown`. |
| 3 | Empty is never sent as zero. | Number fields start empty. Decide stays disabled until required fields are filled. An unread income is sent as `null`, and the reasons contain `income_unknown`. |
| 4 | Text from a model is labelled. | The sentence in `wording` shows "Written by a model and not checked by a person." If `wording` is `null`, no sentence and no label appear. |
| 5 | The page says when the extraction service is down. | Run `docker compose stop extraction`, then upload. The page shows the 503 sentence, and the case worker can still enter every value by hand and decide. |
| 6 | The page says when the backend is down. | Run `docker compose stop backend`, then press Decide. After the timeout the page shows "The backend does not answer. Nothing was decided." No record is created. |
| 7 | One `docker compose up` starts the page too. | On a fresh start the page opens at `localhost:8501`, calls `http://backend:8000`, and starts after the backend is healthy. |
| 8 | Utilisation is asked for and sent as a share. | The field is labelled "as a share, 0.30 is 30%". Entering 0.30 sends 0.30. Entering a value above 1, such as 30, shows the warning "That is above 1 (100%). Did you mean 0.30?" |
| 9 | One click makes one decision. | While a decision is running, Decide is disabled. Press it twice quickly. `GET /decisions/recent` shows one new record, not two. |
| 10 | The page never decides. | The page code contains no scoring, no threshold and no probability. Check by reading the code. |
| 11 | Different people trigger a warning. | If `same_applicant` is `false`, a warning appears (proposal). |
| 12 | The page lists the last 20 decisions. | After a decision, the list shows it at the top with its number, time, outcome and reasons. With `docker compose stop backend`, the page says the list could not be loaded. |

## Decisions made (to copy into the decision log)

- Utilisation is asked for as a share (0.30 is 30%), as in the lecture sketch, so the page does no
  conversion. Because the backend has no upper limit, the page shows a soft warning above 1.
  Values above 1 are still allowed, since an applicant can be over the credit limit.
- Double click: the page disables Decide while a decision is running, so one click makes one record.
  The backend is unchanged. `POST /decisions` is not idempotent, so another caller, such as the
  `/docs` page, can still create two records by sending twice. That is a known limit.
- Recent decisions: the page shows the last 20 (number, time, outcome, reasons), refreshed after each
  decision. This goes beyond the lecture's six steps and is our own addition.

## Open decisions (to settle together, then write into the decision log)

- How long does the page wait for each call (timeout)? Decided: measure first. The page timeout must be
  longer than the backend's worst case, or the page gives up while the backend is still working.
  Known: the backend gives Model C 60 s and then answers without a sentence. A cold start of Model C
  can take 90 s to 3 min. Not yet measured: the time of `POST /extractions`, and the time of
  `POST /decisions` apart from Model C. To do (Gaspar, on the running system): time both calls once
  right after `docker compose up` (cold) and once again (warm), for example with
  `curl -s -o /dev/null -w "%{time_total}\n" ...`, then set each timeout from the result plus a margin.
- Is age typed in, or calculated from the date of birth that was read?
- Confirm the two proposals: the warning when `same_applicant` is `false`, and manual entry when
  extraction is down.
