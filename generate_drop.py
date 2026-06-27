#!/usr/bin/env python3
import json, os, re, sys
from datetime import date
import anthropic

TODAY = date.today().isoformat()
DROPS_PATH = "drops.json"
INDEX_PATH = "index.html"

SYSTEM_PROMPT = """You write a daily AI briefing called The Daily Drop.

Audience: Business professionals in operations, strategy, project management, and admin roles.
They are AI-curious but sometimes apprehensive. Your job is to make them feel capable, not left behind.

Tone: Direct, clear, warm. Not hype. Not fear. Real news, real implications, human voice.

Do NOT mention any company, brand, or organization name in the content. No employer names, no community or program names — only AI tool/platform names when directly relevant to a story.

Format rules:
- Exactly 3 trends per drop
- Each trend has: title, body (2-3 sentences with ONE stat/quote in <em> tags), slants (4 roles), challenge (4-5 steps)
- body must include a real, specific source (publication name + date) inside the <em> block
- challenge steps 2 and 4 must include a copy-paste AI prompt wrapped in <em> tags
- homework: a fun, PERSONAL at-home exercise — NOT work-related. Something the reader does for themselves: plan a trip, explore a hobby, cook something, plan a fun weekend. Low-stakes, enjoyable. Should feel like a reward, not more work."""

def load_drops():
    if not os.path.exists(DROPS_PATH):
        return {}
    with open(DROPS_PATH, encoding="utf-8-sig") as f:
        return json.load(f)

def save_drops(drops):
    with open(DROPS_PATH, "w", encoding="utf-8") as f:
        json.dump(drops, f, indent=2, ensure_ascii=False)

def generate():
    client = anthropic.Anthropic()
    prompt = f"""Today is {TODAY}. Research and write The Daily Drop for this date.

Use web search to find 3 real AI news stories from the past 7 days. Prioritize:
- New model releases or major capability upgrades
- AI integration into mainstream business software (Microsoft, Google, Salesforce, etc.)
- Research findings on AI productivity, workforce impact, or ROI
- US policy, regulation, or major corporate AI decisions

For each story, write one sentence explaining what it means for each role:
- strategy, operations, pm, admin

The homework must be something fun and personal the reader can do at home — NOT work tasks. Examples: plan a weekend trip, write a recipe, brainstorm a bucket list, plan a date night, find a new hobby. It should feel like a treat.

OUTPUT: Return ONLY valid JSON. No markdown. No code fences.

{{
  "intro": "2 sentences. Day of week + thematic thread.",
  "trends": [
    {{
      "title": "Short editorial headline",
      "body": "2-3 sentences. Key stat in <em>source, date</em>.",
      "slants": {{"strategy": "...", "operations": "...", "pm": "...", "admin": "..."}},
      "challenge": {{"steps": ["Step 1: Open your company-approved AI tool.", "Step 2: Paste: <em>\\"prompt here\\"</em>", "Step 3: Note one thing from the output.", "Step 4: Ask a follow-up: <em>\\"follow-up here\\"</em>", "Step 5: Share one insight in the community group."]}}
    }}
  ],
  "homework": {{
    "title": "Short fun invitation — personal, not work.",
    "body": "1-2 sentences setting up the personal exercise.",
    "prompt": "A specific copy-paste prompt for something fun and personal."
  }}
}}"""

    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}]
    resp = client.messages.create(
        model="claude-opus-4-6", max_tokens=5000,
        system=SYSTEM_PROMPT, tools=tools,
        messages=[{"role": "user", "content": prompt}]
    )
    text = "".join(b.text for b in resp.content if hasattr(b, "text"))
    m = re.search(r'\{[\s\S]*\}', text)
    if not m:
        raise ValueError(f"No JSON: {text[:500]}")
    return json.loads(m.group())

def to_js(d, e):
    lines = [f'"{d}": {{', f'    intro: {json.dumps(e["intro"])},', '    trends: [']
    for i, t in enumerate(e.get("trends", [])):
        c = "," if i < len(e["trends"])-1 else ""
        lines += ['      {', f'        title: {json.dumps(t["title"])},', f'        body: {json.dumps(t["body"])},']
        if "slants" in t:
            lines.append('        slants: {')
            sk = list(t["slants"].items())
            for j,(k,v) in enumerate(sk):
                lines.append(f'          {k}: {json.dumps(v)}{"," if j<len(sk)-1 else ""}')
            lines.append('        },')
        if "challenge" in t:
            ch = t["challenge"]
            if isinstance(ch, dict) and "steps" in ch:
                lines += ['        challenge: {', '          steps: [']
                for si,s in enumerate(ch["steps"]):
                    lines.append(f'            {json.dumps(s)}{"," if si<len(ch["steps"])-1 else ""}')
                lines += ['          ]', '        }']
        lines.append(f'      }}{c}')
    lines.append('    ],')
    if "homework" in e:
        hw = e["homework"]
        lines += ['    homework: {', f'      title: {json.dumps(hw.get("title",""))},',
                  f'      body: {json.dumps(hw.get("body",""))},',
                  f'      prompt: {json.dumps(hw.get("prompt",""))}', '    }']
    lines.append('  }')
    return '\n  '.join(lines)

def inject_html(entry):
    with open(INDEX_PATH, encoding="utf-8") as f:
        html = f.read()
    if f'"{TODAY}"' in html:
        print("index.html already up to date.")
        return
    start = html.find("const DROPS = {")
    if start < 0:
        return
    after = start + len("const DROPS = {")
    m = re.search(r'"(\d{4}-\d{2}-\d{2})":', html[after:])
    if not m:
        return
    pos = after + m.start()
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html[:pos] + to_js(TODAY, entry) + ",\n  " + html[pos:])
    print("index.html updated.")

def main():
    drops = load_drops()
    if TODAY in drops:
        print(f"{TODAY} already published.")
        sys.exit(0)
    print(f"Generating {TODAY}...")
    entry = generate()
    drops[TODAY] = entry
    save_drops(drops)
    inject_html(entry)
    print("Done.")

if __name__ == "__main__":
    main()
