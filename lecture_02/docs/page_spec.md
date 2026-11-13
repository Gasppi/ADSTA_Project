# Case worker's page: requirements

Status (update when you change a part):
- [x] 1. User and task
- [x] 2. Flow and design guidelines
- [x] 3. Interface sheets (from `contracts.py` and `router.py`)
- [x] 4. States of the screen
- [x] 5. Acceptance criteria
- [x] Decisions made (near the bottom of this file). The timeouts are provisional.

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
   number (`record_id`). An approval has no reasons, and the page then says "No rule failed."
7. **See the recent decisions.** A list of the last 20 decisions from `GET /decisions/recent`:
   decision number, time, outcome and reasons in words. It loads when the page opens and refreshes
   after each decision.

Every decision rests on documents that were read. If the extraction service is down, the page says
so and the case worker cannot decide until it works again. The page always sends the `checkpoint`
that step 1 returned.

### Rules that follow from the contract

- A value that could not be read is shown as "could not be read". It is sent as `null`. It is never
  filled with 0, `false` or a guess.
- Number fields start empty, never with a prefilled number, so an empty field cannot look like an answer.
- Income is sent as `Money` with currency `CHF` and the period shown on the screen.
- An empty income field means nobody could establish the income. It is sent as `null`, never as 0.
  If the case worker clears an income that was read, it is sent as `null` too.
- The income amount must be above 0. The page refuses 0 and negative amounts. The backend's `Money`
  has no lower limit, and an income of 0 makes `build_features` divide by zero, which gives a 500.
- The loss certificate has three choices: none recorded (`false`), recorded (`true`) and could not be
  read (`null`). Nothing is preselected.
- Reasons are shown in plain words:

| Reason code | Text on the page |
|---|---|
| `default_probability_above_threshold` | The estimated probability of default is above the bank's limit. |
| `loss_certificate_open` | The register shows an open loss certificate. |
| `loss_certificate_unknown` | The loss certificate could not be read. |
| `income_unknown` | The income could not be established. |

- An approved decision has an empty `reasons` list, and the page then says "No rule failed." A refused
  decision always has at least one reason. An unread income or an unread loss certificate always gives
  `refused`, with `income_unknown` or `loss_certificate_unknown` (`rules.py`).
- The sentence in `wording` is labelled "Written by a model and not checked by a person." If
  `wording` is `null`, the page shows the reasons only and no sentence.
- If `same_applicant` is `false`, the page says that the documents name different people and keeps
  Decide disabled. The case worker must upload other documents. If `same_applicant` is `null`, the
  page says "could not be checked" and does not block.

### Design guidelines applied (Amershi et al., 2019)

| Guideline | On this page |
|---|---|
| G2: make clear how well the system can do what it can | The model-written sentence is labelled as unchecked. |
| G9: support efficient correction | The case worker can correct every value that Model B read. |
| G10: scope services when in doubt | A value that could not be read says so. The page never guesses it. |
| G11: make clear why the system did what it did | A refusal always comes with its reasons. An approval says that no rule failed. |

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

The code comment says `payslip.gross` is monthly, but its type `Money` also allows an annual period.
The backend converts an annual `monthly_income` to a monthly amount (`as_monthly`), so the page passes
the confirmed amount and its period through unchanged.

Errors: 422 if a file is missing. 503 if the extraction service is down, with
`{"detail": "The Information Extraction Service is not available. Try again."}`.
The 503 covers every failure of the extraction service: no answer, too late, an error status (for
example a rejected document) and an answer that is not the expected JSON (`clients/extraction.py`).
The page cannot tell these cases apart.
Timeout of the page: 200 s (provisional, not measured). The backend waits up to 180 s for the
extraction service (`read=180.0` in `clients/http.py`), so the page must wait longer than that.

### POST /decisions (page to backend, JSON)

Body: `{"entered": {...}, "extraction_checkpoint": string or null}`.
Send the `checkpoint` that the extraction returned. The backend also accepts `null`, but our page
always has read documents, so it always sends the checkpoint.

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
| `monthly_income` | Money or null | amount above 0 (page rule), currency `CHF`, period `monthly` or `annual` | `null` if nobody could establish it. Never 0 |
| `has_loss_certificate` | bool or null | open loss certificate on the register | `null` if nobody could read it. Never false |

Money looks like `{"amount": "6000.00", "currency": "CHF", "period": "monthly"}`.

Answer 200, `DecisionResponse`:

| Field | Type | Meaning |
|---|---|---|
| `outcome` | `approved` or `refused` | decided by the backend rules, never by the page |
| `reasons` | list of reason codes | `default_probability_above_threshold`, `loss_certificate_open`, `loss_certificate_unknown`, `income_unknown`. Empty when `approved`, at least one when `refused` |
| `wording` | string or null | sentence written by Model C. `null` if Model C is not configured, failed or timed out. A timeout still returns 200 without a sentence |
| `features` | object | six numbers: `age`, `dependents`, `rev_util`, `late_90`, `monthly_inc` (CHF per month) and `debt_ratio` (monthly debt obligations divided by monthly income). The last two are `null` when income is `null` |
| `default_probability` | number or null | probability of default. `null` when a registered Model A cannot score because income is missing. The baseline never returns `null` |
| `model_version` | string | which scorer decided, as `collection:version` (for example `model-a:v5`), or `gaspar-baseline-v1` when no `MODEL_A` is set |
| `record_id` | integer | id of the stored decision |

The outcome is `refused` when there is at least one reason and `approved` when there is none.

Errors: 422 if the body does not fit. 500 if scoring or storing fails (read from `service.py`, where
nothing handles it; not seen in practice). An income of 0 currently gives a 500 until the backend
rejects it with a 422 (read from the code, to be confirmed on the running system). This endpoint never
returns the extraction 503, because `decide()` does not call the extraction service. Every POST
creates a new record, so two clicks make two decisions. If the page gives up first, the backend keeps
working and may still store the decision.
Timeout of the page: 90 s (provisional). The backend gives Model C 60 s and then answers without a sentence.

### GET /health

Answer 200 `{"status": "ok"}`. Use it to check that the backend is up.

### GET /decisions/recent?limit=20 (page to backend)

Answer 200, a list of stored decisions. The page uses `id`, `created_at`, `outcome` and `reasons`.
The backend returns the list newest first (`order_by(DecisionRecord.id.desc())` in `records.py`).
The page keeps that order.
Note: the stored record spells `dependents`, the request spells `dependants`.
The page always sends `limit=20`. The code does not check the range of `limit`, so other values are
not specified (not verified).

## 4. States of the screen

| State | When | What the page shows |
|---|---|---|
| Empty | at the start | No documents. Every number field is empty. Decide is disabled until the documents were read and every required field has a value. |
| Waiting | a call is running | "Reading the documents..." during `POST /extractions`. "Deciding..." during `POST /decisions`. |
| Not read | a value came back `null` | "could not be read" in a highlight, next to the field. The case worker can correct it or leave it. |
| Service down | a call failed | A message that says what failed and what happened. See the table below. |
| The answer | `POST /decisions` returned 200 | Outcome, reasons in words (or "No rule failed." for an approval), the model-written sentence with its label, and the decision number. |

Every answer the page can get has its own sentence:

| What comes back | What the page shows |
|---|---|
| no connection (the backend is stopped) | "The backend does not answer. Nothing was decided." |
| `POST /decisions`: no answer in time | "The backend did not answer in time. The decision may still have been recorded. Check the list of recent decisions before deciding again." |
| `POST /extractions`: no answer in time | "The backend did not answer in time. Nothing was decided. Try again." |
| 422 | "A field is missing or does not fit." The page names the field from `detail`. |
| 503 from `POST /extractions` | "The extraction service gave no result. It may be down, or it may have rejected a document. Try again later or check the documents. Nothing can be decided without the documents." |
| 500, or any other 5xx, from `POST /decisions` | "The backend failed and returned no decision. Check the list of recent decisions before deciding again." |
| 200 | The outcome, as in "The answer" above. |
| the recent list cannot be loaded | "The list of recent decisions could not be loaded." The rest of the page keeps working. |
| the recent list is empty | "No decisions yet." |

## 5. Acceptance criteria

| # | Requirement | How to check it |
|---|---|---|
| 1 | A case worker completes a decision through the page. | Upload both sample documents, correct if needed, fill the rest, press Decide. Outcome, reasons (or "No rule failed." for an approval) and a decision number appear. `GET /decisions/recent` lists that decision. |
| 2 | A value nobody could read says so. | With a document whose loss certificate cannot be read, or by choosing "could not be read", the page shows "could not be read". The answer's reasons contain `loss_certificate_unknown`. |
| 3 | Empty is never sent as zero. | Number fields start empty. Decide stays disabled until required fields are filled. An unread income is sent as `null`, and the reasons contain `income_unknown`. |
| 4 | Text from a model is labelled. | The sentence in `wording` shows "Written by a model and not checked by a person." If `wording` is `null`, no sentence and no label appear. |
| 5 | The page says when the extraction service is down. | Run `docker compose stop extraction`, then upload. The page shows the 503 sentence and Decide stays disabled. After `docker compose start extraction` (it may take a while to become healthy), uploading works again. |
| 6 | The page says when the backend is down. | Run `docker compose stop backend`, then press Decide. The page shows "The backend does not answer. Nothing was decided." right away (a stopped backend refuses the connection; the 90 s timeout only applies to a backend that is up but slow). No record is created. |
| 7 | One `docker compose up` starts the page too. | On a fresh start the page opens at `localhost:8501`, calls `http://backend:8000`, and starts after the backend is healthy. |
| 8 | Utilisation is asked for and sent as a share. | The field is labelled "as a share, 0.30 is 30%". Entering 0.30 sends 0.30. Entering a value above 1, such as 30, shows the warning "That is above 1 (100%). Did you mean 0.30?" |
| 9 | One click makes one decision. | While a decision is running, Decide is disabled. Press it twice quickly. `GET /decisions/recent` shows one new record, not two. |
| 10 | The page never decides. | The page code contains no scoring, no threshold and no probability. Check by reading the code. |
| 11 | Documents of different people block the decision. | If `same_applicant` is `false`, the page says so and Decide stays disabled. Uploading matching documents enables it again. If `same_applicant` is `null`, the page says "could not be checked" and Decide stays enabled. |
| 12 | The page lists the last 20 decisions. | After a decision, the list shows it at the top with its number, time, outcome and reasons. With `docker compose stop backend`, the page says the list could not be loaded. |
| 13 | Income must be above 0. | Enter an income of 0 and of -100. The page refuses both and sends nothing to the backend. An empty income field is sent as `null`. |
| 14 | A slow backend is not reported as "nothing was decided". | Run `docker compose pause backend`, press Decide and wait for the 90 s timeout. The page shows the "did not answer in time" sentence. Then run `docker compose unpause backend`. (Not yet tried.) |

## Decisions made (to copy into the decision log)

- Utilisation is asked for as a share (0.30 is 30%), as in the lecture sketch, so the page does no
  conversion. Because the backend has no upper limit, the page shows a soft warning above 1.
  Values above 1 are still allowed, since an applicant can be over the credit limit.
- Double click: the page disables Decide while a decision is running, so one click makes one record.
  The backend is unchanged. `POST /decisions` is not idempotent, so another caller, such as the
  `/docs` page, can still create two records by sending twice. That is a known limit.
- Different people: the page blocks Decide when `same_applicant` is `false`. The only way on is to
  upload other documents. Known limit: if Model B misreads a name, a legitimate case is blocked
  until other files are found. The backend does not use `same_applicant`, so this rule lives only
  in the page.
- No manual entry: the page requires the documents. If the extraction service is down, nothing can be
  decided until it works again. Known limit: one failing service stops all decisions, although the
  backend itself would accept an application without documents.
- Age: the case worker types it. The date of birth that Model B read is shown beside it for a
  cross-check, and an unread date of birth blocks nothing. The page does no date calculation.
- Recent decisions: the page shows the last 20 (number, time, outcome, reasons), refreshed after each
  decision. This goes beyond the lecture's six steps and is our own addition.
- Income above 0: the page refuses an income of 0 or less. The backend should also reject it with a
  422 (`Money.amount` above 0, with a test), requested from Gaspar. Known limit: an applicant with no
  income cannot be entered as 0. The page can only send `null`, so the decision is refused with the
  reason `income_unknown`.
- Timeouts (provisional): 90 s for `POST /decisions` and 200 s for `POST /extractions`. The 90 s is
  the 60 s that the backend gives Model C plus a margin of 30 s that is not measured. The 200 s is the
  180 s that the backend gives the extraction service plus a margin of 20 s, because the time of
  `POST /extractions` has never been measured. The page reads both values
  from environment variables, so changing them needs no code change.

## To do after the merge

- Backend (Gaspar): reject an income of 0 or less with a 422 and add a test. First confirm, with one
  request on the running system, that an income of 0 gives a 500 now. Then remove the 500 note for
  income 0 in the sheet above.
- Not verified yet: what `GET /decisions/recent` does for a `limit` outside the normal range, and
  whether an empty `MODEL_C` setting becomes `None` (`config.py` was not read).
- Measure the timeouts (Gaspar, on the running system). Time `POST /extractions` and `POST /decisions`
  once right after `docker compose up` (cold) and once again (warm), for example with
  `curl -s -o /dev/null -w "%{time_total}\n" ...`. A page timeout must be longer than the backend's
  worst case, or the page gives up while the backend is still working. Replace the provisional values
  in this file and in `docker-compose.yaml`, and record the measured times in the decision log.
