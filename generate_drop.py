#!/usr/bin/env python3
import json, os, re, sys
from datetime import date
import anthropic

TODAY = date.today().isoformat()

def load_drops():
    if not os.path.exists("drops.json"):
        return {}
    with open("drops.json", encoding="utf-8-sig") as f:
        return json.load(f)

def save_drops(drops):
    with open("drops.json", "w", encoding="utf-8") as f:
        json.dump(drops, f, indent=2, ensure_ascii=False)

def generate():
    client = anthropic.Anthropic()
    prompt = f"""Today is {TODAY}. Write The Daily Drop for NovaLink Studios.

Research 3 real AI news stories from the past 7 days. For each: enterprise impact, role-specific slants (strategy/operations/pm/admin), a 4-step challenge with copy-paste prompts in <em> tags. Add a homework section. Cite real sources with dates inside <em> tags.

Return ONLY valid JSON, no markdown, no code fences:
{{
  "intro": "2 sentences setting up the day.",
  "trends": [
    {{
      "title": "Headline",
      "body": "2-3 sentences. Key stat in <em>source, date</em>.",
      "slants": {{"strategy": "...", "operations": "...", "pm": "...", "admin": "..."}},
      "challenge": {{"steps": ["Step 1.", "Step 2: Paste: <em>\\"prompt\\"</em>", "Step 3.", "Step 4: Ask: <em>\\"follow-up\\"</em>", "Step 5: Share in community."]}}
    }}
  ],
  "homework": {{"title": "...", "body": "...", "prompt": "..."}}
}}"""

    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}]
    resp = client.messages.create(
        model="claude-opus-4-6", max_tokens=5000,
        tools=tools,
        messages=[{"role": "user", "content": prompt}]
    )
    text = "".join(b.text for b in resp.content if hasattr(b, "text"))
    m = re.search(r'\{[\s\S]*\}', text)
    if not m:
        raise ValueError(f"No JSON in response: {text[:500]}")
    return json.loads(m.group())

def inject_html(entry):
    with open("index.html", encoding="utf-8") as f:
        html = f.read()
    if f'"{TODAY}"' in html:
        print("index.html already has today — skipped.")
        return
    start = html.find("const DROPS = {")
    if start < 0:
        print("WARNING: DROPS not found in index.html")
        return
    after = start + len("const DROPS = {")
    m = re.search(r'"(\d{4}-\d{2}-\d{2})":', html[after:])
    if not m:
        return
    pos = after + m.start()
    js = to_js(TODAY, entry)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html[:pos] + js + ",\n  " + html[pos:])
    print("index.html updated.")

def to_js(d, e):
    lines = [f'"{d}": {{', f'    intro: {json.dumps(e["intro"])},', '    trends: [']
    for i, t in enumerate(e.get("trends", [])):
        c = "," if i < len(e["trends"])-1 else ""
        lines += ['      {', f'        title: {json.dumps(t["title"])},', f'        body: {json.dumps(t["body"])},']
        if "slants" in t:
            lines.append('        slants: {')
            sk = list(t["slants"].items())
            for j, (k, v) in enumerate(sk):
                lines.append(f'          {k}: {json.dumps(v)}{"," if j < len(sk)-1 else ""}')
            lines.append('        },')
        if "challenge" in t:
            ch = t["challenge"]
            if isinstance(ch, dict) and "steps" in ch:
                lines += ['        challenge: {', '          steps: [']
                for s_i, s in enumerate(ch["steps"]):
                    lines.append(f'            {json.dumps(s)}{"," if s_i < len(ch["steps"])-1 else ""}')
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

def main():
    drops = load_drops()
    if TODAY in drops:
        print(f"Already published for {TODAY}.")
        sys.exit(0)
    print(f"Generating {TODAY}...")
    entry = generate()
    drops[TODAY] = entry
    save_drops(drops)
    inject_html(entry)
    print("Done.")

if __name__ == "__main__":
    main()
