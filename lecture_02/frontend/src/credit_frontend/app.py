"""The case worker's page. Start it with `streamlit run src/credit_frontend/app.py`.

Streamlit runs this whole script again on every click. What must survive lives in
st.session_state, and the backend is called only when documents are uploaded, when Decide is
pressed, and for the recent list when the page opens and after each decision.

The page never decides. See credit_frontend.logic for everything that is not a Streamlit call.
"""

from typing import Any

import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from credit_frontend import logic
from credit_frontend.backend import BackendClient, Failure, Upload
from credit_frontend.config import ConfigError, load_settings

st.set_page_config(page_title="Credit decision", layout="centered")

try:
    settings = load_settings()
except ConfigError as error:
    st.error(str(error))
    st.stop()

client = BackendClient(
    settings.backend_url,
    extraction_timeout_seconds=settings.extraction_timeout_seconds,
    decision_timeout_seconds=settings.decision_timeout_seconds,
)
state = st.session_state

DEFAULTS: dict[str, Any] = {
    "read_pair": None,  # the file ids of the two documents that were sent last
    "extraction": None,  # the ExtractionResult of those documents, or None
    "extraction_error": None,
    "deciding": False,
    "decision": None,  # the last DecisionResponse, or None
    "decision_error": None,
    "recent_due": True,  # load the recent list on this run
    "recent": None,
    "recent_error": False,
}
for key, default in DEFAULTS.items():
    if key not in state:
        state[key] = default


def not_read_marker() -> None:
    st.markdown(f":orange-background[{logic.NOT_READ}]")


def as_upload(file: UploadedFile) -> Upload:
    return Upload(name=file.name, content=file.getvalue(), content_type=file.type)


def read_documents(payslip: UploadedFile, register: UploadedFile) -> None:
    """POST /extractions, then fill the fields with what was read."""
    with st.spinner("Reading the documents..."):
        answer = client.extract(as_upload(payslip), as_upload(register))
        if isinstance(answer, Failure):
            state.extraction_error = logic.extraction_failure_text(answer)
            return
        state.extraction = answer
        gross = answer["payslip"].get("gross")
        # These widgets are drawn further down, so their values can still be set here.
        state.income_amount = logic.read_income_amount(gross)
        state.income_period = gross.get("period") if gross else None
        state.loss_certificate = logic.loss_certificate_choice(
            answer["debt_register"].get("has_loss_certificate")
        )


def read_again() -> None:
    state.read_pair = None


def start_deciding() -> None:
    state.deciding = True
    state.decision = None
    state.decision_error = None


def whole(value: float | None) -> int | None:
    return None if value is None else int(value)


def number(value: float | None) -> float | None:
    return None if value is None else float(value)


st.title("Credit application")

# --- 1. Documents --------------------------------------------------------------------------

st.header("1. Documents")
left, right = st.columns(2)
payslip_file = left.file_uploader("Payslip", key="payslip_file")
register_file = right.file_uploader("Debt register extract", key="register_file")

pair = (payslip_file.file_id, register_file.file_id) if payslip_file and register_file else None
if pair != state.read_pair:
    # Other documents: what was read and decided belongs to the old ones.
    state.read_pair = pair
    state.extraction = None
    state.extraction_error = None
    state.decision = None
    state.decision_error = None
    if payslip_file is not None and register_file is not None:
        read_documents(payslip_file, register_file)

if state.extraction_error:
    st.error(state.extraction_error)
if pair is not None and state.extraction is None:
    st.button("Read the documents again", on_click=read_again)
elif pair is None:
    st.caption("Upload both documents. They are read as soon as both are here.")

# --- 2. What was read ----------------------------------------------------------------------

extraction = state.extraction
gross_read = extraction["payslip"].get("gross") if extraction else None
register_read: dict[str, Any] = extraction["debt_register"] if extraction else {}

if extraction is not None:
    st.header("2. What was read")
    rows = [
        ("Gross income", logic.format_money(gross_read)),
        (
            "Loss certificate",
            logic.loss_certificate_choice(register_read.get("has_loss_certificate")).value,
        ),
        ("Applicant's name", register_read.get("applicant_name") or logic.NOT_READ),
        ("Date of birth", register_read.get("date_of_birth") or logic.NOT_READ),
    ]
    for label, text in rows:
        name_column, value_column = st.columns([1, 2])
        name_column.markdown(f"**{label}**")
        if text == logic.NOT_READ:
            with value_column:
                not_read_marker()
        else:
            value_column.text(text)

    same_applicant = extraction.get("same_applicant")
    same_text = logic.same_applicant_text(same_applicant)
    if same_applicant is False:
        st.error(same_text)
    elif same_applicant is None:
        st.warning(same_text)
    else:
        st.success(same_text)
    st.caption(f"Read by {extraction['checkpoint']}")

# --- 3. Check and complete the application -------------------------------------------------

st.header("3. The application")
st.caption("Every value that was read can be corrected. Empty fields are never sent as 0.")

income_column, period_column, income_marker = st.columns([2, 1, 1])
# No min_value: the page refuses 0 and negative amounts with its own sentence below, instead of
# Streamlit silently putting the value back.
income_amount = income_column.number_input(
    logic.FIELD_LABELS["monthly_income"],
    value=None,
    step=100.0,
    format="%.2f",
    key="income_amount",
    help="Leave it empty if nobody could establish the income. It is then sent as unknown.",
)
income_period = period_column.selectbox(
    logic.FIELD_LABELS["income_period"],
    options=logic.PERIODS,
    index=None,
    placeholder="Choose",
    key="income_period",
)
if extraction is not None and gross_read is None:
    with income_marker:
        not_read_marker()
income_problem = logic.income_problem(number(income_amount))
if income_problem:
    st.error(income_problem)

certificate_column, certificate_marker = st.columns([3, 1])
loss_certificate = certificate_column.radio(
    logic.FIELD_LABELS["has_loss_certificate"],
    options=list(logic.LossCertificate),
    index=None,
    format_func=lambda choice: choice.value,
    horizontal=True,
    key="loss_certificate",
)
if extraction is not None and register_read.get("has_loss_certificate") is None:
    with certificate_marker:
        not_read_marker()

age_column, birth_column = st.columns([2, 2])
age = age_column.number_input(
    logic.FIELD_LABELS["age"], min_value=18, max_value=120, value=None, step=1, key="age"
)
if extraction is not None:
    with birth_column:
        date_of_birth = register_read.get("date_of_birth")
        if date_of_birth:
            st.caption(f"Date of birth as read, to cross-check: {date_of_birth}")
        else:
            st.caption("Date of birth as read:")
            not_read_marker()

counts: dict[str, int | None] = {}
first, second = st.columns(2)
for index, name in enumerate(logic.REQUIRED_INTEGERS[1:]):
    column = first if index % 2 == 0 else second
    counts[name] = whole(
        column.number_input(logic.FIELD_LABELS[name], min_value=0, value=None, step=1, key=name)
    )

utilisation = st.number_input(
    logic.UTILISATION_LABEL,
    min_value=0.0,
    value=None,
    step=0.01,
    format="%.2f",
    key="revolving_utilisation",
)
warning = logic.utilisation_warning(number(utilisation))
if warning:
    st.warning(warning)

debt_obligations = st.number_input(
    logic.FIELD_LABELS["monthly_debt_obligations"],
    min_value=0.0,
    value=None,
    step=50.0,
    format="%.2f",
    key="monthly_debt_obligations",
)

values = logic.EnteredValues(
    age=whole(age),
    dependants=counts["dependants"],
    open_credit_lines=counts["open_credit_lines"],
    real_estate_lines=counts["real_estate_lines"],
    late_30_59=counts["late_30_59"],
    late_60_89=counts["late_60_89"],
    late_90=counts["late_90"],
    revolving_utilisation=number(utilisation),
    monthly_debt_obligations=number(debt_obligations),
    income_amount=number(income_amount),
    income_period=income_period,
    loss_certificate=loss_certificate,
)

# --- 4. Decide -----------------------------------------------------------------------------

st.header("4. Decide")
blockers = logic.decide_blockers(extraction=extraction, values=values, deciding=state.deciding)
st.button("Decide", type="primary", disabled=bool(blockers), on_click=start_deciding)

if state.deciding:
    # The button above was drawn disabled before this call starts, so a second click
    # cannot start a second decision.
    if extraction is None or logic.decide_blockers(
        extraction=extraction, values=values, deciding=False
    ):
        state.deciding = False
        st.rerun()
    body = logic.build_decision_body(values, extraction["checkpoint"])
    try:
        with st.spinner("Deciding..."):
            answer = client.decide(body)
            if isinstance(answer, Failure):
                state.decision_error = logic.decision_failure_text(answer)
            else:
                state.decision = answer
    finally:
        state.deciding = False
        state.recent_due = True
    st.rerun()

for blocker in blockers:
    st.caption(blocker)

# --- 5. The answer -------------------------------------------------------------------------

if state.decision_error:
    st.error(state.decision_error)

decision = state.decision
if decision is not None:
    st.header("5. The answer")
    st.subheader(f"Outcome: {decision['outcome']}")
    st.markdown(f"**Decision number:** {decision['record_id']}")
    st.markdown("**Reasons**")
    for text in logic.reason_texts(decision["reasons"]):
        st.markdown(f"- {text}")
    wording = logic.wording_to_show(decision)
    if wording is not None:
        with st.container(border=True):
            st.caption(logic.WORDING_LABEL)
            st.text(wording)

# --- 6. Recent decisions -------------------------------------------------------------------

st.header("Recent decisions")
if state.recent_due:
    with st.spinner("Loading the recent decisions..."):
        recent = client.recent()
        state.recent_error = isinstance(recent, Failure)
        state.recent = None if isinstance(recent, Failure) else recent
        state.recent_due = False

if state.recent_error:
    st.warning(logic.RECENT_NOT_LOADED)
elif not state.recent:
    st.info(logic.NO_DECISIONS)
else:
    st.dataframe(logic.recent_rows(state.recent), hide_index=True)
