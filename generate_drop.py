#!/usr/bin/env python3
import json, os, re, sys
import urllib.request
from datetime import date

try:
    import anthropic as _anthropic
except ImportError:
    _anthropic = None


TODAY = date.today().isoformat()
DROPS_PATH = "drops.json"
INDEX_PATH = "index.html"

# Content source: industry-trends-ref generates first (9:45 UTC),
# this repo fetches that content 15 min later (10:00 UTC).
INDUSTRY_TRENDS_DROPS_URL = (
    "https://raw.githubusercontent.com/novalinkstudios/Industry-trends/main/drops.json"
)


def load_drops():
    if not os.path.exists(DROPS_PATH):
        return {}
    with open(DROPS_PATH, encoding="utf-8-sig") as f:
        return json.load(f)


def save_drops(drops):
    with open(DROPS_PATH, "w", encoding="utf-8") as f:
        json.dump(drops, f, indent=2, ensure_ascii=False)


def fetch_source():
    """Pull the full industry-trends archive so we can backfill any gaps."""
    print("Fetching archive from industry-trends...")
    try:
        with urllib.request.urlopen(INDUSTRY_TRENDS_DROPS_URL, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"Could not fetch industry-trends drops.json: {e}")



def _generate_leaders_slant(title, body, strategy):
    """Generate a leaders slant via Claude API, or fall back to strategy."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or _anthropic is None:
        return strategy
    try:
        client = _anthropic.Anthropic(api_key=api_key)
        prompt = (
            f"Title: {title}\nBody: {body}\nStrategy slant: {strategy}\n\n"
            "Write a 1-2 sentence 'Leaders' perspective for a manager or org leader "
            "deciding how to direct their team around this AI trend. "
            "Focus on an action or decision they should make NOW for their organization "
            "(not just for themselves personally). Under 45 words. No bullet points."
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"Warning: leaders slant generation failed ({e}); using strategy as fallback.")
        return strategy


def ensure_leaders_slants(entry):
    """Add a 'leaders' key to any trend slants block that's missing it."""
    for trend in entry.get("trends", []):
        slants = trend.get("slants", {})
        if slants and "leaders" not in slants:
            leaders = _generate_leaders_slant(
                trend.get("title", ""),
                trend.get("body", ""),
                slants.get("strategy", ""),
            )
            # Insert leaders right after strategy
            new_slants = {}
            for k, v in slants.items():
                new_slants[k] = v
                if k == "strategy":
                    new_slants["leaders"] = leaders
            trend["slants"] = new_slants
    return entry


def to_js(d, e):
    lines = [f'"{d}": {{', f'    intro: {json.dumps(e["intro"])},', '    trends: [']
    for i, t in enumerate(e.get("trends", [])):
        c = "," if i < len(e["trends"]) - 1 else ""
        lines += ['      {', f'        title: {json.dumps(t["title"])},',
                  f'        body: {json.dumps(t["body"])},']
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
                for si, s in enumerate(ch["steps"]):
                    lines.append(f'            {json.dumps(s)}{"," if si < len(ch["steps"])-1 else ""}')
                lines += ['          ]', '        }']
        lines.append(f'      }}{c}')
    lines.append('    ],')
    if "homework" in e:
        hw = e["homework"]
        lines += ['    homework: {',
                  f'      title: {json.dumps(hw.get("title", ""))},',
                  f'      body: {json.dumps(hw.get("body", ""))},',
                  f'      prompt: {json.dumps(hw.get("prompt", ""))}',
                  '    }']
    lines.append('  }')
    return '\n  '.join(lines)


def inject_html(day, entry):
    with open(INDEX_PATH, encoding="utf-8") as f:
        html = f.read()
    if f'"{day}"' in html:
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
        f.write(html[:pos] + to_js(day, entry) + ",\n  " + html[pos:])
    print(f"index.html updated for {day}.")


def main():
    drops = load_drops()
    source = fetch_source()

    missing = sorted(d for d in source if d not in drops)
    if not missing:
        print("Already in sync with industry-trends — nothing to publish.")
        sys.exit(0)

    if TODAY not in source:
        print(f"Note: industry-trends has no entry for {TODAY} yet.")

    print(f"Publishing {len(missing)} drop(s): {', '.join(missing)}")
    for day in missing:
        entry = ensure_leaders_slants(source[day])
        drops[day] = entry
        inject_html(day, entry)
    save_drops(drops)
    print("Done.")


if __name__ == "__main__":
    main()
