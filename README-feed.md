# The Daily Drop — feed format (`drops.json`)

`index.html` ships with a built-in archive of past drops baked into the page.
On load it also fetches **`drops.json`** from the site root and merges those
entries on top of the archive (matching dates override). This is the file the
**`daily-ai-trends` scheduled task writes to** so new drops appear without
editing `index.html`.

## How it works

1. Page loads → renders the built-in archive immediately.
2. `fetch('drops.json')` runs → entries are merged into the in-memory `DROPS`.
3. The view jumps to the most recent drop on or before today.

If `drops.json` is missing or unreachable, the page still renders the built-in
archive — the fetch fails silently.

## Format

`drops.json` is a single JSON object keyed by date (`"YYYY-MM-DD"`). Each date
maps to one drop:

```jsonc
{
  "2026-06-17": {
    "intro": "One or two sentences setting up the day. Plain text.",

    "trends": [
      {
        "title": "Short headline",
        "body": "1–3 sentences. Inline <em>…</em> HTML is allowed for emphasis.",

        // OPTIONAL — role-specific takes. Keys: strategy | operations | pm | admin.
        // Omit the whole object for a plain news item.
        "slants": {
          "strategy":   "One sentence.",
          "operations": "One sentence.",
          "pm":         "One sentence.",
          "admin":      "One sentence."
        },

        // OPTIONAL — a community action. Either a list of steps OR a string.
        // Omit entirely to skip.
        "challenge": { "steps": ["Step one.", "Step two.", "Step three."] }
        // or:  "challenge": "A single sentence prompt."
      }
      // …any number of trends; the site renders however many you provide.
    ],

    // OPTIONAL — the "Homework" accordion at the bottom. Omit to skip.
    "homework": {
      "title": "Headline for the homework block.",
      "body": "Setup sentence(s).",
      "prompt": "The copy-paste prompt. Inline HTML (<em>, <br>) allowed."
    }
  }
}
```

### Field reference

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `<date>` | yes | object | Key format `YYYY-MM-DD`. One per drop. |
| `intro` | yes | string | Lead-in shown under the date. |
| `trends` | yes | array | One entry per story. Any length. |
| `trends[].title` | yes | string | Headline. |
| `trends[].body` | yes | string | Summary; inline `<em>` allowed. |
| `trends[].slants` | no | object | Keys: `strategy`, `operations`, `pm`, `admin`. Any subset. |
| `trends[].challenge` | no | object \| string | `{ "steps": [...] }` or a plain string. |
| `homework` | no | object | `{ title, body, prompt }`. |

HTML allowed inside string values: `<em>`, `<strong>`, `<br>`. Everything else
is rendered as text. Keep quotes inside strings escaped (`\"`) per JSON rules.

## What the scheduled task should do

Each run, the `daily-ai-trends` task should **add one new dated key** for the
current day and write the merged object back to `drops.json` (keep prior dates
so the archive grows). Minimum viable entry:

```json
{
  "2026-06-18": {
    "intro": "…",
    "trends": [
      { "title": "…", "body": "…" }
    ]
  }
}
```

Adding `slants`, `challenge`, and `homework` makes a day match the richer
editorial format used by the hand-written archive, but they are all optional —
a bare `title` + `body` per trend renders cleanly.

After writing `drops.json`, redeploy the site (Netlify) so the new file is
served.
