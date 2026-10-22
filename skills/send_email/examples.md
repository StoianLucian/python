# Send Email — Response Format

Answer in **Markdown**, confirming only the outcome of the `send_email` tool.

## Output Format

- One short confirmation line.
- Never include the email subject or body, and never paraphrase the email back.
- Never write the response as if you were the email itself.
- If the tool reported `success: false`, briefly say it couldn't be sent and why.

---

## Example 1 — Email sent

Tool:
```json
{ "success": true, "result": "Email sent successfully to user 15" }
```

Response:
```markdown
Email sent successfully.
```

---

## Example 2 — Email sent to a named recipient

Tool:
```json
{ "success": true, "result": "Email sent successfully to user 23" }
```

Response:
```markdown
Email sent to **Sarah**.
```

---

## Example 3 — Tool failed

Tool:
```json
{ "success": false, "result": "User not found" }
```

Response:
```markdown
The email could not be sent: user not found.
```

---

## Example 4 — Recipient missing, no tool call made

```markdown
Please mention the recipient (e.g. @John) so I know who to email.
```

---

## Incorrect

Never return the email itself, e.g. **do not** respond with:

```markdown
Hi Sarah, just letting you know I'll be about 15 minutes late.
```
