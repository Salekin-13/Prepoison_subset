# llm.py -- shared LLM helpers (used by Stage A, S2 summaries, P1 parsing)
import re, json, time, random
from google.genai import types

def parse_json_array(text):
    t = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.M).strip()
    i, j = t.find("["), t.rfind("]")
    if i != -1 and j != -1 and j > i:
        t = t[i:j+1]
    try:
        a = json.loads(t)
        return a if isinstance(a, list) else []
    except Exception:
        return []

def complete_text(client, system, user, max_tokens=2048):
    wait = 2.0
    for a in range(client.r):
        try:
            return client.c.models.generate_content(
                model=client.model, contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system, temperature=client.t,
                    max_output_tokens=max_tokens)).text
        except Exception as e:
            if "PerDay" in str(e): raise      # daily quota: don't retry
            if a == client.r - 1: raise
            time.sleep(wait + random.uniform(0, 1)); wait *= 2