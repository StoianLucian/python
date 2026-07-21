# Skill: Send Email

## Purpose

Use this skill whenever the user wants to send an email to one or more people.

Examples:
- "Email John that the meeting is postponed."
- "Send Sarah the latest report."
- "Tell Alex I'll be late."

---

## Workflow

1. Identify the intended recipient(s).
2. Resolve each recipient using the `search_users` tool.
3. If no matching user is found:
   - Ask the user who they meant.
4. If multiple users match:
   - Ask the user to choose the correct recipient.
5. Once the recipient has been resolved:
   - Use the returned `id` for all subsequent actions.
   - Never guess or invent an email address.
6. Generate a clear email subject if the user did not provide one.
7. Generate a professional email body from the user's request.
8. Call `send_email`.

---

## Tool Usage

### search_users

Input

```json
{
  "query": "John"
}
```

Example output

```json
{
  "success": true,
  "users": [
    {
      "id": 15,
      "name": "John Smith",
      "email": "john.smith@company.com"
    }
  ]
}
```

---

### send_email

Input

```json
{
  "user_id": 15,
  "subject": "Meeting postponed",
  "body": "Hi John,\n\nThe meeting has been postponed until tomorrow.\n\nThanks."
}
```

---

## Rules

- Never invent recipients.
- Never invent email addresses.
- Always resolve the recipient first.
- Always use the returned user id.
- Ask for clarification when multiple users match.
- Ask for clarification when the recipient is missing.

---

## Example

User:

> Email John that tomorrow's meeting has moved to 3 PM.

Assistant reasoning:

1. search_users("John")
2. send_email(
       user_id=15,
       subject="Meeting moved to 3 PM",
       body="Hi John,..."
   )

Return the normal success response.