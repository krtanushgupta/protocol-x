# UNMISSED — Hackathon Development Record

> **Repository note:** This file is in the root of the inspected UNMISSED project at `C:\Users\TANUSH K GUPTA\OneDrive\Desktop\letsee`. A README was not present. Git could not be run in this environment and no `.git` directory was visible, so the GitHub remote, commit history, and exact historical file-change mapping could not be verified. Items marked **Unknown** or **requires confirmation** are intentionally left unresolved.

## 1. Project Overview

- **Project name:** UNMISSED
- **Problem:** People returning to long group chats may miss deadlines, requests, decisions, questions, and useful announcements in a large volume of messages.
- **Target users:** People who need to catch up on long WhatsApp conversations, including group-chat participants and students or teams using chats to coordinate work.
- **Core functionality currently present:** Paste conversation text or upload a WhatsApp `.txt` export; parse recognizable messages; produce a concise overview and evidence-linked findings organized under three priorities and topic groups; inspect original messages and open extracted links.
- **Intended outcome:** Help a user understand what may need attention while retaining access to the source messages so they can judge the context themselves.

## 2. Technology Stack and Architecture

### Verified implementation

- **Frontend:** Static HTML, CSS, and browser JavaScript. The frontend is in `frontend/`; it is not a React/TypeScript application.
- **Backend:** Python and FastAPI, served by Uvicorn. The FastAPI application serves both the API and the static frontend from the same origin by default.
- **API:** `POST /api/analyze` accepts a JSON `text` field. Pydantic request/response schemas constrain input and output. The handler calls the analysis pipeline, validates source evidence, then validates the response model.
- **Analysis:** Deterministic Python and regular-expression rules. No local LLM, cloud LLM API, model name, or AI provider configuration was found in the inspected source, dependency list, or `.env.example`.
- **Parsing:** Recognizes several WhatsApp-style date/time/sender headers, appends continuation lines to the previous message, extracts HTTP(S) links, and filters recognized pure system membership events from findings.
- **Finding generation:** Uses rule-based patterns for action verbs, questions, topic names, priority, selected deadlines, announcement titles, and links. It consolidates normalized duplicates and has a conservative token-overlap fallback for task/question matches in the same topic. Evidence validation checks that source IDs, timestamps, senders, text, and URLs match the supplied conversation.
- **Limits:** The analysis/schema limit is 1,000,000 characters; the API body middleware rejects request bodies over 8,100,000 bytes. The browser upload control accepts `.txt` and limits the selected file to 1 MB. The frontend request timeout is 120 seconds.
- **PWA:** `frontend/manifest.webmanifest` declares standalone display and app icons. `frontend/sw.js` caches the app shell and skips API requests; the service worker does not provide offline analysis.
- **Configuration:** `.env.example` currently contains only `UNMISSED_CORS_ORIGINS`. No model credentials or provider settings are present.

### Planned or not verified

- No LLM-assisted analysis is implemented in the inspected code. Any future model integration would require an explicit provider, structured output, evidence validation, and clear consent/disclosure before sending conversations to a third party.
- Browser/device installation, offline app-shell behavior, and deployment behavior have not been comprehensively verified on target mobile devices or a production HTTPS host.
- There is no README in the inspected project; setup instructions currently derive from `run_unmissed.bat` and the Python dependency file.

## 3. Development Plan

### MVP features

1. Accept pasted WhatsApp text and exported `.txt` files; preserve the input on failure.
2. Parse message timestamps, senders, and multiline text; exclude pure membership system events.
3. Extract candidate tasks, questions, decisions, announcements, deadlines, and URLs with deterministic logic.
4. Link findings to original source messages; validate evidence and links before returning results.
5. Show exactly `URGENT`, `IMPORTANT`, and `FYI`; organize findings under relevant topic groups and filters.
6. Provide a responsive PWA shell with source inspection, loading/error feedback, and reduced-motion support.

### Implementation sequence

1. Inspect the existing project and preserve its working frontend and analysis behavior.
2. Keep parsing, analysis, evidence validation, schemas, and API routes in separate modules.
3. Connect the input screen to the API and validate source-linked results.
4. Organize results by topic and priority, with compact controls and expandable source messages.
5. Verify API behavior, PWA assets, responsive styling, privacy behavior, and failure states.

This sequence is a development plan, not a claim that every verification step has been completed.

### Important requirements and constraints

- Evidence over confident-sounding summaries; do not fabricate messages, people, assignments, dates, decisions, links, or sources.
- Preserve conflicting evidence and disclose unresolved conflicts. Do not infer a confirmed deadline from an ambiguous date.
- Keep distinct tasks separate; consolidate only when the messages support the match.
- Keep private conversation text out of persistent storage and logs by default; avoid databases unless a real product need arises.
- Do not claim local-only processing for a remotely hosted API.

### Future improvements

- Add robust behavior for additional WhatsApp export locales and formats, with explicit unsupported-format feedback.
- Improve and evaluate deadline interpretation, duplicate matching, question/answer linking, and topic classification against diverse synthetic cases.
- Verify the installable PWA and offline app shell on Android and desktop browsers.
- Add end-to-end UI tests for filtering, source expansion, errors, responsive layouts, and reduced motion.
- If AI analysis is ever added, keep keys server-side, request user consent before external transmission, and reject unsupported structured claims against source evidence.

## 4. AI-Assisted Development Log

The conversation history available for this task establishes the broad tasks below, but does not provide reliable dates or model identifiers for older development work. The local workspace has no usable Git history, so the listed files are current implementation areas, not verified per-task diffs.

| Date | AI Tool / Model | Actual Prompt or Task | Purpose | Files Affected | Outcome | Verification |
|---|---|---|---|---|---|---|
| Unknown; earlier conversation | Codex; exact model unknown | Earlier requests asked for WhatsApp parsing, evidence-backed findings, three priorities, and a small UNMISSED micro-app. | Establish the product and analysis requirements. | Exact historical changes cannot be mapped; current related code is in `backend/pipeline/`, `backend/schemas.py`, and `frontend/`. | The current project contains a rule-based parser/analysis pipeline and a two-screen input/results interface. | Current source inspected; historical prompt dates and exact diff require confirmation. |
| Unknown; earlier conversation | Codex; exact model unknown | Requests asked to diagnose a `Failed to fetch` error for a long chat, retain input on failure, filter membership events, and test large input/API behavior. | Improve request handling and evidence-linked analysis. | Exact historical changes cannot be mapped; current related code is in `backend/app.py`, `backend/pipeline/`, `frontend/app.js`, and `tests/test_pipeline.py`. | Current code has request/body limits, a frontend timeout/error path, and a test for a 72,343-character API request. The original reported browser failure's root cause and fix are not established by this record. | A prior session report stated **40 tests passed**, but the command/date were not preserved here. This task did not rerun them. Browser-level reproduction of the reported failure remains pending. |
| Unknown; earlier conversation | Codex; exact model unknown | Requests asked for more specific findings, clickable source URLs, topic grouping, duplicate consolidation, deadlines, and expandable evidence. | Make results more useful without inventing source facts. | Exact historical changes cannot be mapped; current related code is in `backend/pipeline/analysis.py`, `backend/pipeline/parsing.py`, `backend/pipeline/validation.py`, `frontend/app.js`, and `tests/test_pipeline.py`. | Current implementation has rule-based topic/deadline extraction, source validation, link rendering, filters, and evidence controls. | Current source and test definitions inspected. No tests were run for this documentation task. |
| Unknown; earlier conversation | Codex; exact model unknown | Styling requests specified Crimson Protocol, then X-CORE colors, an X intro, topic filters, responsive compact groups, and reduced-motion behavior. | Evolve the visual identity while retaining the PWA interface. | Exact historical changes cannot be mapped; current related code is in `frontend/index.html`, `frontend/style.css`, `frontend/results.css`, and `frontend/app.js`. | Current files contain the X-inspired intro, topic filters, expandable groups, responsive rules, reduced-motion CSS, and X-CORE color overrides. | Current source inspected; visual/browser regression testing remains pending. |
| Unknown; earlier conversation | Codex; exact model unknown | Requests asked to refactor the project into a full-stack PWA, use FastAPI if compatible, separate the pipeline, validate API responses, and document privacy. | Structure the frontend/backend and analysis boundaries. | Exact historical changes cannot be mapped; current related code is in `backend/app.py`, `backend/schemas.py`, `backend/pipeline/`, `server.py`, `requirements.txt`, and `frontend/`. | Current project uses FastAPI and a static HTML/CSS/JavaScript PWA; no model API or database was found. | Current files inspected. The earlier session reported 40 tests passed; exact command/date are unknown and require confirmation. |
| 2026-10-09 | Codex; exact model unknown | Read-only audit request: identify the analysis method/provider, trace Analyze and data flow, inspect dependencies/configuration, and assess offline behavior. | Explain actual analysis and privacy behavior from source. | None; read-only inspection. | Determined that the current pipeline is rule-based and sends text to the configured same-origin backend; no model/provider configuration was found. | Source/dependency/config inspection; no files modified. |
| 2026-10-09 | Codex; exact model unknown | Request to inspect and start the existing website using `run_unmissed.bat`'s configured command, fix startup issues, and verify the URL. | Make the app viewable locally. | No application files changed; a Uvicorn process was started for this session. | Port 8000 was occupied by a process whose health route returned 404; the current FastAPI app was started on port 8001 instead. | `http://127.0.0.1:8001/` returned HTTP 200 and `/api/health` returned `{"status":"ok"}`. This is a startup check, not a suite test. |
| 2026-10-09 | Codex; exact model unknown | Current request: inspect the repository and create this root `prompt.md`, documenting only supportable implementation history, requirements, privacy, tests, and next steps. | Preserve a truthful hackathon development record. | `prompt.md` only. | Created this document; historical uncertainty is called out rather than filled with guesses. | Confirmed file exists at the project root and reviewed its Markdown sections and factual caveats. No application tests run. |

## 5. Key Product Requirements

- Every factual finding should link to one or more actual source messages, retaining sender and timestamp when available.
- Do not fabricate facts, quotes, deadlines, tasks, decisions, URLs, people, or references.
- Use exactly these priority labels: `URGENT`, `IMPORTANT`, and `FYI`.
- Exclude pure WhatsApp group-membership system notifications such as joining via invite link, adding, leaving, or removal. Preserve human-written messages about people joining a team or project.
- Organize relevant findings by topics such as Register/Registrations & Forms, Assignments & Submissions, Homework & Doubts, Classes & Attendance, Deadlines & Reminders, and Announcements & FYI. Topics are not extra priorities.
- Preserve distinct tasks and their separate evidence when consolidating duplicate reminders.
- Show exact or safely resolved deadlines only when supported; disclose conflicts and ambiguous dates.
- Keep findings concise, actionable, traceable, and supported by expandable original messages.
- Preserve original URLs and render only valid HTTP(S) links from evidence.

## 6. UI/UX and Design Decisions

- **Product identity:** PROTOCOL X / Crimson Protocol / X-CORE, using an original angular X mark and wordmark.
- **Current stylesheet tokens/overrides:** midnight `#0A0B12`; surfaces `#151722` and `#202333`; crimson `#FF294F`; orange `#FF7138`; cyan `#24D9FF`; lime `#C8FF38`; violet `#9B6DFF`; primary text `#F8F9FF`; secondary text `#B8BDCE`; borders `#34384A`.
- The current interface includes an X-inspired opening animation, topic filter tabs, compact collapsible topic groups, source-message expansion, responsive CSS, and reduced-motion handling.
- The intended visual hierarchy uses crimson/orange for the brand and urgency, cyan for interactive details, and lime sparingly for positive states. Content surfaces must keep body text readable.
- Filters are derived from actual result topics; they do not create findings or change priority labels.
- Animation should be brief and restrained, support keyboard interaction, and respect `prefers-reduced-motion`.

## 7. Privacy and Security

- **Current data flow:** The browser sends the pasted or uploaded conversation text in a JSON `POST` to `/api/analyze`. FastAPI parses and analyzes it in the request handler, validates the response against the submitted text, and returns findings and source messages.
- **Local vs remote:** The development launcher binds the server to `127.0.0.1:8000` (the currently started session used port 8001 because 8000 was occupied). When the backend is run on the same device, the request is processed by that local server. If the app is deployed with a remote backend, conversation content leaves the device and is sent to that backend. The source alone does not establish where a deployed instance runs.
- **Storage:** The inspected API handler has no database or file-persistence operation for conversations; findings remain in the active response/UI. The service worker skips `/api/` and caches app-shell assets only. This supports no intentional application-level permanent storage in the inspected path, but does not guarantee behavior of hosting providers, proxies, browser memory, backups, or deployment logging.
- **Third parties:** No LLM provider call or AI API key configuration was found. Do not describe this as a universal privacy guarantee; the browser-to-backend transmission still occurs.
- **Secrets:** Do not put API keys, credentials, personal chats, or other secrets in this file. `.env.example` contains only an empty CORS-origin setting.
- **Deployment requirement:** Use HTTPS for remote hosting and clearly disclose the receiving server before users submit private conversations. Review access/proxy logging and cache headers before making broader privacy claims.

## 8. Testing and Verification

### Tests/verification reported as run

- **Earlier session report:** 40 tests passed after backend/API work. The exact command and date are not present in the available record; reconfirmation is pending. Do not treat this entry as a fresh run.
- **2026-10-09 startup check:** The current app's homepage at `http://127.0.0.1:8001/` returned HTTP 200 and `/api/health` returned `{"status":"ok"}`.
- **This documentation task:** Root location and contents were inspected. No application tests were run because no application code was changed.

### Pending verification checklist

- [ ] Rerun the current test suite and record the exact command, count, and result.
- [ ] Reproduce and diagnose the previously reported browser `Failed to fetch` error with the original long conversation. The root cause and fix are **not established** by the available evidence.
- [ ] Verify the actual browser Analyze flow for pasted text and `.txt` uploads, including network failure and timeout behavior.
- [ ] Test topic filter counts/reset, expandable evidence, clickable links, keyboard access, and reduced-motion mode in a browser.
- [ ] Verify responsive behavior and PWA installation on Android and desktop.
- [ ] Verify offline shell loading separately from analysis; `/api/` requests are not service-worker-cached, so analysis requires a reachable backend.
- [ ] Review remote deployment HTTPS, CORS, proxy/access logs, request-size/time limits, and cache headers before deployment.

### Known limitations/issues

- The earlier browser `Failed to fetch` issue for a large conversation was reported. Although current tests include a 72,343-character API case and the configured API accepts larger inputs up to its limits, that does not prove the original browser/network failure was fixed. Its root cause remains unknown/requires reproduction.
- The rule-based pipeline can miss or misinterpret informal, localized, ambiguous, or context-dependent language. It is not an LLM and does not provide a guarantee of accuracy.
- Relative-date resolution depends on recognized and unambiguous source timestamps; the project has no reliable timezone configuration for each conversation.
- PWA installability and offline shell behavior are configured in source but have not been comprehensively verified across devices.
- The GitHub remote and commit history could not be inspected in this environment.

## 9. Current Status and Next Steps

### Verified current state

- A FastAPI backend serves the static HTML/CSS/JavaScript PWA and exposes health and analysis routes.
- The current analysis is rule-based, with WhatsApp parsing, membership-event exclusion, priority/topic rules, deadline extraction, duplicate handling, source/link validation, and typed response schemas.
- The PWA manifest and service worker are present; the service worker caches shell assets and bypasses API traffic.
- A local app instance was verified on `http://127.0.0.1:8001/` during the 2026-10-09 startup task. The configured launcher still targets port 8000, which was occupied by another process during that check.
- This `prompt.md` was created at the project root. No application files were changed for this documentation task.

### Next steps

1. Rerun tests and capture the exact command/result.
2. Reproduce the large-chat browser error and establish whether it is a server, browser, proxy, timeout, or deployment issue before claiming a fix.
3. Complete browser/device checks for analysis flow, accessibility, responsiveness, PWA installability, and offline shell behavior.
4. Before remote deployment, configure HTTPS and review CORS, request limits, logs, and privacy disclosure.
5. Update this log after each meaningful AI-assisted development task, using verifiable details.

## 10. Ongoing Update Rules

- Update `prompt.md` after every meaningful AI-assisted development task.
- Record the actual prompt or a faithful summary, the tool used, files affected, outcome, and verification.
- Identify an AI model only when the evidence names it; otherwise write **exact model unknown**.
- Use **Unknown** or **requires confirmation** for unavailable dates, historical diffs, and commands.
- Record failed attempts and corrections honestly. Keep an earlier reported result distinct from a test run performed now.
- Do not rewrite history, infer GitHub actions without evidence, or fabricate prompts, file changes, outcomes, or test results.
- Never include API keys, credentials, personal conversation text, or private user data.
