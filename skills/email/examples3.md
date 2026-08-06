# `/send_email` Skill Examples

This document contains examples of the `/send_email` skill mention format and the corresponding tool invocation.

---

## Example 1

### Serialized Input

```js
[
  {
    "type": "skill-mention",
    "attrs": {
      "id": 1,
      "label": "/send_email"
    }
  },
  {
    "type": "text",
    "text": " to "
  },
  {
    "type": "user-mention",
    "attrs": {
      "id": 15,
      "label": "John"
    }
  },
  {
    "type": "text",
    "text": " saying tomorrow's meeting has moved to 3 PM"
  }
]
```

### User

> Email John that tomorrow's meeting has moved to 3 PM.

### Assistant reasoning

- The user wants to send an email.
- The recipient is John.
- Generate an appropriate subject and body.

### Example output

```json
send_email(
  user_id=15,
  subject="Tomorrow's Meeting Moved to 3 PM",
  body="Hi John,\n\nJust letting you know that tomorrow's meeting has been moved to 3:00 PM.\n\nSee you then!"
)
```

---

## Example 2

### Serialized Input

```js
[
  {
    "type": "skill-mention",
    "attrs": {
      "id": 1,
      "label": "/send_email"
    }
  },
  {
    "type": "text",
    "text": " to "
  },
  {
    "type": "user-mention",
    "attrs": {
      "id": 23,
      "label": "Sarah"
    }
  },
  {
    "type": "text",
    "text": " saying I will be about 15 minutes late"
  }
]
```

### User

> Email Sarah that I'll be about 15 minutes late.

### Assistant reasoning

- The user wants to send an email.
- The recipient is Sarah.
- Generate a concise subject and body.

### Example output

```json
send_email(
  user_id=23,
  subject="Running Late",
  body="Hi Sarah,\n\nJust a quick note to let you know that I'll be about 15 minutes late.\n\nSee you soon!"
)
```

---

## Example 3

### Serialized Input

```js
[
  {
    "type": "skill-mention",
    "attrs": {
      "id": 1,
      "label": "/send_email"
    }
  },
  {
    "type": "text",
    "text": " to "
  },
  {
    "type": "user-mention",
    "attrs": {
      "id": 31,
      "label": "Alex"
    }
  },
  {
    "type": "text",
    "text": " thanking them for their help last week"
  }
]
```

### User

> Email Alex thanking them for their help last week.

### Assistant reasoning

- The user wants to send an email.
- The recipient is Alex.
- Compose a polite thank-you email.

### Example output

```json
send_email(
  user_id=31,
  subject="Thank You",
  body="Hi Alex,\n\nI just wanted to thank you for all your help last week. I really appreciate your support.\n\nThanks again!"
)
```

---

## Example 4

### Serialized Input

```js
[
  {
    "type": "skill-mention",
    "attrs": {
      "id": 1,
      "label": "/send_email"
    }
  },
  {
    "type": "text",
    "text": " to "
  },
  {
    "type": "user-mention",
    "attrs": {
      "id": 42,
      "label": "Emily"
    }
  },
  {
    "type": "text",
    "text": " asking if she is available for lunch on Friday"
  }
]
```

### User

> Email Emily asking if she's available for lunch on Friday.

### Assistant reasoning

- The user wants to send an email.
- The recipient is Emily.
- Generate an appropriate subject and email body.

### Example output

```json
send_email(
  user_id=42,
  subject="Lunch on Friday?",
  body="Hi Emily,\n\nI was wondering if you're available for lunch this Friday. Let me know if that works for you!\n\nLooking forward to hearing from you."
)
```