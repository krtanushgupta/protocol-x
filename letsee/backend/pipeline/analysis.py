"""Evidence-linked topic classification, grouping, and deadline handling."""
from __future__ import annotations
import re
from .parsing import parse_messages, is_group_event, _extract_links, _finding_sentences

MAX_CHARS = 1_000_000
ACTION = re.compile(r"\b(fill\s+out|complete|submit|send|share|upload|register|bring|arrive|report|attend|respond|reply|vote|choose|create|prepare|check|confirm|join|apply|keep|make\s+sure|be\s+present)\b", re.I)

ACTION_HEAD = {"fill out":"Complete", "complete":"Complete", "submit":"Submit", "send":"Send", "share":"Share", "upload":"Upload", "register":"Register", "bring":"Bring", "arrive":"Arrive", "report":"Report", "attend":"Attend", "respond":"Respond", "reply":"Reply", "vote":"Vote", "choose":"Choose", "create":"Create", "prepare":"Prepare", "check":"Check", "confirm":"Confirm", "join":"Join", "apply":"Apply", "keep":"Keep", "make sure":"Make sure", "be present":"Be present"}

def _action_match(sentence: str):
    match=ACTION.search(sentence)
    if not match: return None
    verb=match.group(1).lower()
    target=re.split(r"\b(?:by|before|today|tomorrow|tonight|as soon as|so that|so we|so i|to help|if|when)\b",sentence[match.end():],maxsplit=1,flags=re.I)[0]
    target=re.sub(r"\s+"," ",target.strip(" \t:;,.-"))
    target=re.sub(r"\s+(?:please|kindly|immediately|asap)$","",target,flags=re.I)
    if len(target)>65: target=target[:62].rsplit(" ",1)[0]+"…"
    return {"verb":verb,"head":ACTION_HEAD.get(verb,verb.title()),"target":target,"sentence":sentence}

def _explicit_deadline(sentence: str) -> str | None:
    pattern=(r"\b(?:by|before|due(?:\s+on)?|deadline(?:\s+is|\s*:)?|no\s+later\s+than)\s+"
             r"(?:today|tomorrow|tonight|eod|end\s+of\s+day|\d{1,2}(?::\d{2})?(?:\s?[ap]m)?(?:\s+(?:today|tomorrow|on\s+)?(?:mon|tues|wednes|thurs|fri|satur|sun)day)?|"
             r"(?:mon|tues|wednes|thurs|fri|satur|sun)day|\d{1,2}(?:st|nd|rd|th)?\s+[a-z]+|[a-z]+\s+\d{1,2}(?:st|nd|rd|th)?|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b|"
             r"\b(?:today|tomorrow|tonight)\b")
    match=re.search(pattern,sentence,re.I)
    return match.group(0).strip() if match else None

def _specific_title(text: str, sentence: str) -> str:
    low=(text+" "+sentence).lower()
    decision=re.search(r"\b(?:we\s+)?decided\s+to\s+([^.!?\n]+)|\bdecision\s*:\s*([^.!?\n]+)",sentence,re.I)
    if decision: return "Decision: "+(decision.group(1) or decision.group(2)).strip(" ,;:.")[:58]
    if "feedback" in low and "form" in low: return "Day 1 feedback form" if "day 1" in low else "Feedback form"
    if "reporting time" in low: return "Reporting time"
    if "scavenger hunt" in low: return "AI scavenger hunt announcement"
    if "registration" in low: return "Registration update"
    if any(word in low for word in ("recruitment","hiring","internship")): return "Recruitment information"
    if "workshop" in low: return "Workshop announcement"
    if "meeting" in low: return "Meeting information"
    if "venue" in low or "location" in low: return "Venue information"
    title=sentence.strip()
    if len(title)>64: title=title[:61].rsplit(" ",1)[0]+"…"
    return title[:1].upper()+title[1:]

def _structured_details(text: str) -> list[str]:
    labels=r"Reporting\s+Time|Deadline|Due|Date|Time|Venue|Location"
    matches=list(re.finditer(rf"\b({labels})\s*:\s*",text,re.I))
    details=[]
    for index,match in enumerate(matches):
        start=match.end()
        end=matches[index+1].start() if index+1<len(matches) else len(text)
        value=re.sub(r"\s+"," ",text[start:end]).strip(" \t-–—,;:.*")
        value=re.split(r"\b(?:Prerequisites|Before the Session|Attendance and Certificates)\s*:",value,1,flags=re.I)[0].strip()
        if value: details.append(f"{match.group(1).strip()}: {value[:90]}")
    return details[:4]

def _is_noise(text: str) -> bool:
    plain=re.sub(r"[^a-z0-9\s]"," ",text.lower())
    plain=" ".join(plain.split())
    return plain in {"", "ok", "okay", "yes", "no", "same", "fine", "lol", "lmao", "haha", "hahaha", "see you", "thanks", "thank you", "good morning", "good night", "gm", "gn"}

def _task_identity_tokens(title: str) -> set[str]:
    tokens=set(re.findall(r"[a-z]+|\b\d+\b",title.lower()))
    ignored={"please","kindly","complete","submit","send","share","upload","register","fill","out","finish","the","a","an","for","to","your","our","by","before"}
    return tokens-ignored

def _build_finding(message: dict) -> dict:
    text=message["text"]
    links=_extract_links(text)
    sentences=_finding_sentences(text,links)
    selected=None; action=None
    for sentence in sentences:
        candidate=_action_match(sentence)
        if candidate:
            selected=sentence; action=candidate; break
    is_question=bool(re.search(r"\b(how do i|how can i|how do we|can someone explain|please explain|anyone know|help me)\b",text,re.I))
    if is_question: action=None
    if action:
        title=(action["head"]+(" "+action["target"] if action["target"] else "")).strip()[:76]
        deadline=_explicit_deadline(selected or "")
        if not deadline:
            deadline=next((_explicit_deadline(sentence) for sentence in sentences if re.search(r"\b(?:deadline|due|by|before|no later than)\b",sentence,re.I) and _explicit_deadline(sentence)),None)
        reason=re.search(r"\bto help\s+(?:us\s+)?([^,;.!?]+)|\bso (?:we|i|it|this)\s+([^,;.!?]+)",selected or "",re.I)
        details=_structured_details(text)
        if reason:
            purpose=(reason.group(1) or reason.group(2)).strip(" ,;:")
            explanation=f"Responses are requested to help {purpose}."
        elif deadline: explanation=f"Group-wide request. Deadline stated: {deadline}."
        else: explanation="Group-wide request; the source names no individual assignee."
        if details: explanation+=" Details: "+"; ".join(details)+"."
        kind="task"
    elif is_question:
        selected=next((s for s in sentences if "?" in s), sentences[0] if sentences else text)
        title=selected.strip()
        if len(title)>76: title=title[:73].rsplit(" ",1)[0]+"…"
        explanation="Question or request for help; no clearly linked reply was identified."
        kind="question"
    else:
        decision=next((s for s in sentences if re.search(r"\b(?:decided|decision|confirmed|cancelled|canceled|changed)\b",s,re.I)),None)
        selected=decision or (max(sentences,key=lambda s:sum(bool(re.search(rf"\b{w}\b",s,re.I)) for w in ("workshop","session","meeting","venue","reporting time","registration","feedback","deadline","date","time","location","prize","announcement"))) if sentences else text)
        title=_specific_title(text,selected)
        explanation=selected if len(selected)<=190 else selected[:187].rsplit(" ",1)[0]+"…"
        kind="decision" if decision else "information"
    if action:
        if _is_urgent_deadline(deadline, message.get("timestamp", "")): priority="URGENT"
        else: priority="IMPORTANT"
    elif kind=="question" or re.search(r"\b(?:decided|decision|confirmed|meeting|poll|vote|question|deadline|interview)\b",text,re.I): priority="IMPORTANT"
    else: priority="FYI"
    topic=_topic_for(text, title, kind)
    deadline=(_resolve_deadline(deadline, message.get("timestamp", "")) or "Not specified") if action else None
    return {"priority":priority,"topic":topic,"title":title,"explanation":explanation,"kind":kind,
            "deadline":deadline,"links":[{"url":link["url"],"label":link["label"]} for link in links],"sources":[message]}

def _topic_for(text: str, title: str, kind: str) -> str:
    value=(text+" "+title).lower()
    if kind=="question": return "Homework & Doubts"
    if re.search(r"\b(register|registration|registrations|sign[- ]?up|feedback form|application|apply|id creation form)\b",value): return "Registrations & Forms"
    if re.search(r"\b(homework|how do i solve|explain question|doubt|help me|how can i solve)\b",value): return "Homework & Doubts"
    if re.search(r"\b(assignment|homework|module\s*\d+|project report|submission|submit)\b",value): return "Assignments & Submissions"
    if re.search(r"\b(class|lecture|lab|attendance|attend|venue|classroom|schedule)\b",value): return "Classes & Attendance"
    if re.search(r"\b(deadline|due|reminder|today|tomorrow|by friday)\b",value) and kind=="task": return "Deadlines & Reminders"
    return "Announcements & FYI"

def _resolve_deadline(deadline: str | None, timestamp: str) -> str | None:
    if not deadline: return None
    relative=re.search(r"\b(today|tomorrow|tonight|(?:mon|tues|wednes|thurs|fri|satur|sun)day)\b",deadline,re.I)
    if not relative: return deadline
    base=_timestamp_date(timestamp)
    if base is None:
        reason="message date ambiguous" if re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",timestamp) else "message date unavailable"
        return f"Not specified (source says {deadline!r}; {reason})"
    from datetime import timedelta
    day_name=relative.group(1).lower()
    weekdays={"monday":0,"tuesday":1,"wednesday":2,"thursday":3,"friday":4,"saturday":5,"sunday":6}
    if day_name in weekdays:
        target_delta=(weekdays[day_name]-base.weekday())%7
        resolved=base+timedelta(days=target_delta)
    else:
        resolved=base+(timedelta(days=1) if day_name=="tomorrow" else timedelta())
    return f"{deadline} ({resolved.strftime('%d %B %Y').lstrip('0')})"

def _timestamp_date(timestamp: str):
    parsed=re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})",timestamp)
    if not parsed: return None
    from datetime import date
    a,b,y=map(int,parsed.groups()); y += 2000 if y<100 else 0
    if a<=12 and b<=12: return None
    day,month=(a,b) if a>12 else (b,a)
    try: return date(y,month,day)
    except ValueError: return None

def _is_urgent_deadline(deadline: str | None, timestamp: str) -> bool:
    if not deadline or not re.search(r"\b(today|tonight|tomorrow|within\s+\d+\s+hours?|eod|end\s+of\s+day)\b",deadline,re.I): return False
    base=_timestamp_date(timestamp)
    if base is None: return False
    from datetime import date, timedelta
    target=base+timedelta(days=1) if re.search(r"\btomorrow\b",deadline,re.I) else base
    return target>=date.today()

def analyze(text: str) -> dict:
    if not isinstance(text,str) or not text.strip(): raise ValueError("Paste a conversation or upload a WhatsApp .txt file first.")
    if len(text)>MAX_CHARS: raise ValueError("This conversation is too large to analyze (limit: 1 MB of text).")
    messages=parse_messages(text)
    if not messages: raise ValueError("No WhatsApp-style messages were recognized. Check that each message has a date, time, sender, and colon.")
    human=[m for m in messages if not is_group_event(m) and m["text"].strip()]
    # Index explicit deadline dates by their subject so many-message exports stay linear.
    deadline_topics={}
    generic_deadlines={}
    conflict_pair=None
    for m in human:
        dates=re.findall(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b",m["text"])
        if dates and re.search(r"\b(?:deadline|due|by|submit|submission)\b",m["text"],re.I):
            # Ignore generic deadline terms and compare the remaining subject words.
            subject=re.sub(r"\b(?:deadline|due|by|submit|submission|is|was|the|a|an|on|for|to|please|date|send|share|complete|finish|upload)\b|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?", " ",m["text"].lower())
            generic={"deadline","due","by","submit","submission","is","was","the","a","an","on","for","to","please","date","send","share","complete","finish","upload","module","assignment","homework","project","report"}
            tokens={w for w in re.findall(r"[a-z]+|\b\d+\b",subject) if (w.isdigit() or len(w)>2) and w not in generic}
            for date in set(dates):
                if tokens:
                    for token in tokens:
                        previous=deadline_topics.setdefault(token,{})
                        if previous and date not in previous and conflict_pair is None:
                            conflict_pair=(next(iter(previous.values())),m)
                        previous.setdefault(date,m)
                else:
                    if generic_deadlines and date not in generic_deadlines and conflict_pair is None:
                        conflict_pair=(next(iter(generic_deadlines.values())),m)
                    generic_deadlines.setdefault(date,m)
    conflicting=conflict_pair is not None
    findings=[]
    # Consolidate only exact normalized titles within the same priority/topic.
    seen={}
    for m in human:
        key=re.sub(r"\W+"," ",m["text"].lower()).strip()
        if key in seen:
            seen[key]["sources"].append(m); continue
        finding=_build_finding(m)
        if conflicting and m in conflict_pair:
            finding["priority"]="IMPORTANT"; finding["explanation"]="Conflicting deadline details appear in the conversation; the outcome is unresolved."
        seen[key]=finding; findings.append(finding)
    # Attach a later reply only when it explicitly refers to the same numbered question
    # and contains explanatory content; ambiguous conversational adjacency is insufficient.
    answered_ids=set()
    for question in findings:
        if question["kind"]!="question": continue
        source=question["sources"][0]
        numbers=set(re.findall(r"\b(?:question|q)\s*(\d+)\b",source["text"],re.I))
        if not numbers: continue
        for reply in human:
            if reply["id"]<=source["id"] or reply["id"] in answered_ids: continue
            reply_numbers=set(re.findall(r"\b(?:question|q)\s*(\d+)\b",reply["text"],re.I))
            if numbers & reply_numbers and re.search(r"\b(use|because|solution|answer|first|step|formula|explain|divide|multiply|calculate)\b",reply["text"],re.I):
                question["sources"].append(reply)
                question["explanation"]="A later message appears to answer this question. Both messages are available as sources."
                answered_ids.add(reply["id"])
                break
    findings=[f for f in findings if not (f["kind"]=="information" and f["sources"][0]["id"] in answered_ids)]
    # Repetitive casual chatter is omitted, but announcements and uncertain useful messages remain FYI.
    meaningful=[]
    for f in findings:
        source=f["sources"][0]["text"]
        if f["priority"]!="FYI" or not _is_noise(source): meaningful.append(f)
    consolidated={}
    for finding in meaningful:
        normalized_title=re.sub(r"\b(the|a|an)\b", " ", finding["title"].lower())
        normalized_title=re.sub(r"\W+"," ",normalized_title).strip()
        key=(finding["topic"], normalized_title)
        if finding["kind"] not in ("task", "question"):
            key+=(str(finding["sources"][0].get("id")),)
        if key not in consolidated and finding["kind"] in ("task", "question"):
            # Similarity is only a fallback within the same topic and task type.
            # Distinct numeric identifiers (for example Module 2 and Module 3) never merge.
            candidate_tokens=_task_identity_tokens(finding["title"])
            candidate_numbers={token for token in candidate_tokens if token.isdigit()}
            for existing_key, existing in consolidated.items():
                if existing_key[0]!=finding["topic"] or existing["kind"]!=finding["kind"]: continue
                prior_tokens=_task_identity_tokens(existing["title"])
                prior_numbers={token for token in prior_tokens if token.isdigit()}
                if candidate_numbers and prior_numbers and candidate_numbers!=prior_numbers: continue
                overlap=candidate_tokens & prior_tokens
                union=candidate_tokens | prior_tokens
                if len(overlap)>=2 and union and len(overlap)/len(union)>=0.65:
                    key=existing_key
                    break
        if key not in consolidated:
            consolidated[key]=finding
            continue
        existing=consolidated[key]
        existing["sources"].extend(finding["sources"])
        known={link["url"] for link in existing["links"]}
        existing["links"].extend(link for link in finding["links"] if link["url"] not in known)
        deadlines={existing.get("deadline"),finding.get("deadline")} - {None,"Not specified"}
        if len(deadlines)>1:
            existing["explanation"]="Conflicting deadline details appear in the conversation; the outcome is unresolved."
            existing["deadline"]="Conflicting deadlines"
            existing["priority"]="IMPORTANT"
        elif len(deadlines)==1: existing["deadline"]=next(iter(deadlines))
        elif finding["priority"]=="URGENT": existing["priority"]="URGENT"
    groups={p:[] for p in ("URGENT","IMPORTANT","FYI")}
    for f in consolidated.values(): groups[f["priority"]].append(f)
    overview=[f"{len(messages)} messages parsed from the conversation."]
    if not human: overview.append("Only group-membership or system events were found; there are no conversation findings.")
    else:
        overview.append(f"{len(consolidated)} concise findings retained, with original messages available as evidence.")
        if conflicting: overview.append("Some deadline messages conflict; no resolution could be established from the available messages.")
    return {"overview":overview,"categories":groups,"message_count":len(messages)}
