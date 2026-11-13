# Prompt for the coding agent: build the case worker's page

Give the agent the text between the lines below, from the root of the repository.

---

Build the page that `lecture_02/docs/page_spec.md` describes. Call the backend at `BACKEND_URL`.

Read `page_spec.md` completely before you write anything. It is the only source of truth for what the
page does. If something in it is unclear or contradicts the code, stop and list the point. Do not
guess.

## Where and how

- Put the page in a new project, `lecture_02/frontend/`, with the package `credit_frontend`. Follow
  the pattern of `lecture_02/extraction_service/`: its own `pyproject.toml`, `uv.lock`,
  `.python-version`, `Dockerfile`, `.dockerignore`, `src/` and `tests/`. Read those files of the
  extraction service first and copy their conventions (Python version, uv, ruff and ty settings,
  Dockerfile style). Do not invent versions.
- Use Streamlit for the page and httpx to call the backend. Add them with `uv add`, so the versions
  are pinned in `uv.lock`.
- Do not change the backend or the extraction service.
- Never put a secret in the code or the repository. Do not commit `.env`.

## Behaviour

- Read `BACKEND_URL` from the environment. Read the two timeouts from the environment variables
  `EXTRACTION_TIMEOUT_SECONDS` and `DECISION_TIMEOUT_SECONDS`. Give none of the three a default in
  the code. The timeouts are not measured yet, so Compose sets provisional values that are
  replaced after measuring.
- The page never decides, never scores and never holds a threshold or a probability rule. The
  backend decides.
- Keep the logic apart from the Streamlit calls, in plain functions that tests can call: building
  the request body (Money, `null` for unread values, utilisation as a share), turning reason codes
  into the texts in the specification, turning each status code and failure into its sentence, and
  sorting the recent list. Test them with pytest. Use `httpx.MockTransport` to test the calls to
  the backend without a running backend.
- Remember that Streamlit runs the whole script on every click. What must survive goes into
  `st.session_state`. Call the backend only on the upload and on Decide, never on every rerun.
- Number fields start empty (`value=None`). An empty field is never sent as 0.

## Docker Compose

- Add a service `frontend` to `lecture_02/docker-compose.yaml`: built from `frontend`, port
  `8501:8501`, `BACKEND_URL=http://backend:8000`, the two timeout variables, `depends_on` the
  `backend` with `condition: service_healthy`, and a health check on `/_stcore/health`. Write the
  health check with `python -c "import urllib.request; ..."` like the other services, since `curl`
  may be missing in a slim image. Do not change the other services.
- One `docker compose up` must start the page together with the rest.

## Quality

- `ruff check`, `ruff format --check`, `ty check` and `pytest` must pass in the new project.
- Look at `.github/workflows` and report whether CI covers the new project. If it does not, say so
  and propose the change. Do not change CI without saying so.

## When you are done

Write a table with the 12 acceptance criteria of the specification. For each one say how the page
meets it, and mark the ones you could not check. Do not claim a check you did not run.
