# Skill: Search Documents

## Purpose

Use this skill whenever the user asks a question that may be answered using the company's knowledge base or stored documents.

Examples include:

- Company policies
- Employee handbook
- Technical documentation
- Internal procedures
- Product documentation
- FAQs
- Previously indexed documents

---

## Workflow

1. Determine whether the user's question requires information from company documentation.
2. Call `search_documents` using the user's question as the search query.
3. Read the returned document excerpts.
4. Answer the user's question using only the retrieved information.
5. If multiple excerpts are returned, combine them into a clear and concise answer.
6. If no relevant documents are found, tell the user.

---

## Rules

- Search before answering when documentation is required.
- Do not invent information that was not retrieved.
- If the retrieved information is incomplete, say so.
- Summarize the retrieved content instead of copying large passages.
- If appropriate, reference the page number(s) where the information was found.