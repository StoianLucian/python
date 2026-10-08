# Skill: Web Search

## Purpose

Use this skill whenever the user asks a question that requires current, real-time,
or external information that is not in the company's own documents.

Examples include:

- Recent news or current events
- Latest versions, releases, or prices
- Facts that change over time (weather, stock prices, standings)
- Information about external companies, products, or people
- Anything the user explicitly asks you to "look up" or "search online"
- Questions where your own knowledge may be outdated

Do **not** use this skill for questions answerable from internal documentation —
use `search_documents` for those.

---

## Workflow

1. Determine whether the question needs fresh or external information from the web.
2. Rewrite the user's request into a concise, keyword-focused search query
   (drop conversational filler; keep the essential terms).
3. Call `web_search` with that query as `use_question`.
4. Read the returned results (title, url, content snippet).
5. If the results are thin, off-topic, conflicting, or leave the question only
   partly answered, search **again with a different query** — broaden it, narrow
   it, or attack the question from another angle to fill the gap. You may do this
   a few times. Do **not** repeat the exact same query; it returns the same
   results and will be rejected.
6. Synthesize a clear, direct answer from the most relevant and recent results
   across **all** the searches you ran.
7. Cite the sources you actually used.
8. If no useful results are returned after refining, tell the user you couldn't
   find anything.

---

## Rules

- Search before answering when the question needs current or external information.
- Base the answer only on the retrieved results — do not invent facts or URLs.
- Prefer recent, authoritative sources; note the date when recency matters.
- If results conflict, say so and present the most credible view.
- Summarize; do not paste large passages verbatim.
- Always cite the URLs of the sources used in the answer.
- If the results are incomplete or ambiguous, refine and search again before
  giving up; only say so if a couple of refined searches still come up short.
- Stop searching once you have enough to answer well — don't keep searching for
  marginal gains.
