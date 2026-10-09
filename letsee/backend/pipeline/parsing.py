"""WhatsApp export parsing and deterministic source extraction."""
from __future__ import annotations
import re
from urllib.parse import urlparse

TIME = r"\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APap][Mm])?"

TIMESTAMP_LINE = re.compile(rf"^\[?(\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}},?\s+{TIME})\]?\s+(?:-\s+)?(.+)$")

HEADER = re.compile(rf"^\[?(\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}},?\s+{TIME})\]?\s+(?:-\s+)?([^:]+):\s?(.*)$")

ALT_HEADER = re.compile(rf"^(\d{{1,2}}/\d{{1,2}}/\d{{2,4}}),?\s+({TIME})\s+(?:-\s+)?([^:]+):\s?(.*)$")

SYSTEM_HEADER = re.compile(rf"^\[?(\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}},?\s+{TIME})\]?\s+(?:-\s+)?(.+)$")

SYSTEM_PATTERNS = [r".+ joined via invite link\.?", r".+ added .+", r".+ left$", r".+ removed .+", r".+ changed the group (?:name|icon|description)", r".+ changed settings:.*", r".+ created (?:the )?group(?: .*)?"]

URL_START = re.compile(r"https?://", re.I)

def parse_messages(text: str) -> list[dict]:
    messages=[]
    for line in text.replace("\ufeff", "").splitlines():
        raw=TIMESTAMP_LINE.match(line)
        if raw:
            content=raw.group(2).strip()
            event_text=content.split(":",1)[0].strip() if ":" in content else content
            if any(re.fullmatch(p,event_text,re.I) for p in SYSTEM_PATTERNS):
                messages.append({"timestamp":raw.group(1).strip(),"sender":"","text":content})
                continue
        m=HEADER.match(line)
        if m:
            messages.append({"timestamp":m.group(1).strip(),"sender":m.group(2).strip(),"text":m.group(3).strip()})
            continue
        m=ALT_HEADER.match(line)
        if m:
            messages.append({"timestamp":f"{m.group(1)} {m.group(2)}","sender":m.group(3).strip(),"text":m.group(4).strip()})
        elif (system:=SYSTEM_HEADER.match(line)):
            messages.append({"timestamp":system.group(1).strip(),"sender":"","text":system.group(2).strip()})
        elif messages and line.strip():
            messages[-1]["text"] += "\n" + line.rstrip()
    for i,m in enumerate(messages): m["id"]=i
    return messages

def is_group_event(message: dict) -> bool:
    t=message["text"].strip()
    return not message["sender"] and any(re.fullmatch(p,t,re.I) for p in SYSTEM_PATTERNS)

def _extract_links(text: str) -> list[dict]:
    """Extract literal HTTP(S) links and join only obvious line-wrap breaks."""
    links=[]
    for match in URL_START.finditer(text):
        start=match.start()
        if any(link["start"]<=start<link["end"] for link in links): continue
        i=start; chars=[]
        while i<len(text):
            c=text[i]
            if c in " \t<>\"'`()[]{}": break
            if c in "\r\n":
                j=i+1
                if c=="\r" and j<len(text) and text[j]=="\n": j+=1
                if (chars and chars[-1] in "/?&=#%") or text[j:j+1] in "/?&=#%": i=j; continue
                break
            chars.append(c); i+=1
        raw_value="".join(chars)
        value=raw_value.rstrip(".,;!:")
        while value.endswith(")") and value.count("(")<value.count(")"): value=value[:-1]
        parsed=urlparse(value)
        if parsed.scheme.lower() not in ("http","https") or not parsed.netloc: continue
        end=i-(len(raw_value)-len(value))
        left=text[max(0,start-120):start].lower()
        hint_matches=list(re.finditer(r"\b(feedback\s+form|registration\s+form|form|spreadsheet|sheet|document|agenda|meeting|zoom|teams|registration|register|sign\s+up|event)\b",left))
        hint=hint_matches[-1].group(1) if hint_matches else ""
        context=(hint+" "+text[end:min(len(text),end+80)].lower()).strip()
        if "feedback" in context and ("form" in context or "survey" in context): label="Open feedback form ↗"
        elif "registration form" in context: label="Open registration form ↗"
        elif "register" in context or "sign up" in context: label="Register ↗"
        elif "form" in context: label="Open form ↗"
        elif any(w in context for w in ("spreadsheet","sheet","document","agenda")): label="View document ↗"
        elif any(w in context for w in ("meeting","zoom","teams")): label="Join meeting ↗"
        elif "registration" in context or "event" in context: label="Open registration link ↗"
        else: label="Open link ↗"
        links.append({"url":value,"label":label,"start":start,"end":end})
    return links

def _finding_sentences(text: str, links: list[dict]) -> list[str]:
    chars=list(text)
    for link in links:
        for i in range(link["start"],min(link["end"],len(chars))): chars[i]=" "
    clean="".join(chars).replace("\r","")
    result=[]
    for part in re.split(r"(?<=[.!?])\s+|\n+",clean):
        part=" ".join(part.split()).strip(" -*•\t")
        part=re.sub(r"^\[(?:forwarded|image omitted|video omitted|audio omitted)\]\s*", "", part, flags=re.I)
        if part and not re.fullmatch(r"(?:hey|hello|hi)\s+(?:everyone|all|guys)[,!. ]*",part,re.I): result.append(part)
    return result
