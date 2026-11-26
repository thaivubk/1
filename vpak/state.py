"""Gom sự kiện sổ cái thành trạng thái cho dashboard (hàm thuần, không đọc file)."""
from __future__ import annotations

from datetime import datetime

from .catalog import AGENTS, agent_color

FEED_LIMIT = 30


def _hhmm(ts: str) -> str:
    return ts[11:16] if ts and len(ts) >= 16 else ""


def _name(agent: str) -> str:
    if agent == "user":
        return "Đại ca"
    return AGENTS.get(agent, {}).get("name", agent or "?")


def build_state(events: list[dict], now: datetime | None = None) -> dict:
    jobs: dict[str, dict] = {}
    order: list[str] = []
    tasks: dict[str, dict] = {}
    questions: dict[str, dict] = {}
    feed: list[dict] = []

    def task_of(ev: dict) -> dict | None:
        return tasks.get(ev.get("task", ""))

    def log(task: dict | None, ev: dict, text: str) -> None:
        if task is not None:
            task["log"].append({"t": _hhmm(ev.get("ts", "")), "x": text})

    def add_feed(ev: dict, color: str, text: str) -> None:
        feed.append({"t": _hhmm(ev.get("ts", "")), "c": color, "x": text})

    for ev in events:
        typ, jid = ev.get("type"), ev.get("job", "")
        if typ == "job_created":
            jobs[jid] = {"id": jid, "title": ev.get("title", jid), "folder": ev.get("folder", ""),
                         "kind": ev.get("kind", "tt"), "note": ev.get("note", ""), "status": "run",
                         "pct": 0, "created": ev.get("ts", ""), "tasks": [], "error": ""}
            order.append(jid)
            add_feed(ev, "#1F3A5F", f"Đại ca giao {jid}: {ev.get('title', '')}")
            continue
        job = jobs.get(jid)
        if typ == "task_assigned" and job is not None:
            agent = ev.get("agent", "")
            if agent not in AGENTS:
                continue
            t = {"id": ev.get("task", ""), "job": jid, "from": ev.get("from", "giao-viec"), "to": agent,
                 "desc": ev.get("desc", ""), "status": "wait", "pct": 0, "finds": 0, "issues": [],
                 "log": [], "file": "", "time": _hhmm(ev.get("ts", ""))}
            tasks[t["id"]] = t
            job["tasks"].append(t)
            log(t, ev, "Nhận việc từ Giao việc")
            add_feed(ev, agent_color(agent), f"Giao việc giao {jid} cho {_name(agent)}")
        elif typ == "task_started":
            t = task_of(ev)
            if t:
                t["status"], t["time"] = "run", _hhmm(ev.get("ts", ""))
                log(t, ev, "Bắt đầu làm")
        elif typ == "progress":
            t = task_of(ev)
            if t:
                t["pct"] = max(0, min(100, int(ev.get("pct", 0) or 0)))
                if t["status"] == "wait":
                    t["status"] = "run"
                if ev.get("ghi_chu"):
                    log(t, ev, ev["ghi_chu"])
        elif typ == "finding":
            t = task_of(ev)
            if t:
                t["finds"] += 1
                t["issues"].append({"x": ev.get("text", ""), "ref": ev.get("nguon", ""), "nhan": ev.get("nhan", "")})
                log(t, ev, "Phát hiện: " + ev.get("text", ""))
            add_feed(ev, agent_color(ev.get("agent", "")), f"{_name(ev.get('agent', ''))} phát hiện: {ev.get('text', '')}")
        elif typ == "question":
            t = task_of(ev)
            qid = ev.get("qid", "")
            questions[qid] = {"id": qid, "job": jid, "task": ev.get("task", ""), "agent": ev.get("agent", ""),
                              "q": ev.get("q", ""), "choices": list(ev.get("choices", []))}
            if t:
                t["status"] = "review"
                log(t, ev, "Dừng lại, hỏi đại ca")
            add_feed(ev, "#B45309", f"{_name(ev.get('agent', ''))} hỏi đại ca ({jid})")
        elif typ == "decision":
            q = questions.pop(ev.get("qid", ""), None)
            if q:
                t = tasks.get(q["task"])
                if t and t["status"] == "review":
                    t["status"] = "run"
                log(t, ev, "Đại ca quyết: " + ev.get("answer", ""))
                add_feed(ev, "#B45309", f"Đại ca quyết {q['job']}: {ev.get('answer', '')}")
        elif typ == "task_done":
            t = task_of(ev)
            if t:
                t["status"], t["pct"], t["time"] = "done", 100, _hhmm(ev.get("ts", ""))
                if ev.get("file"):
                    t["file"] = ev["file"]
                log(t, ev, f"Hoàn thành, có {t['finds']} phát hiện" if t["finds"] else "Hoàn thành")
                add_feed(ev, agent_color(t["to"]), f"{_name(t['to'])} xong việc {jid}")
        elif typ == "job_done" and job is not None:
            job["status"] = "done"
            add_feed(ev, "#23804D", f"Xong {jid}")
        elif typ == "error" and job is not None:
            job["status"], job["error"] = "error", ev.get("reason", "")
            add_feed(ev, "#B42318", f"{jid} gặp lỗi: {ev.get('reason', '')}")

    for job in jobs.values():
        ts = job["tasks"]
        job["pct"] = round(sum(t["pct"] for t in ts) / len(ts)) if ts else 0
        if job["status"] == "run" and any(t["status"] == "review" for t in ts):
            job["status"] = "review"

    agents = {}
    for aid in AGENTS:
        mine = [t for t in tasks.values() if t["to"] == aid]
        run = [t for t in mine if t["status"] == "run"]
        rev = [t for t in mine if t["status"] == "review"]
        done = sum(1 for t in mine if t["status"] == "done")
        cur = run[0] if run else (rev[0] if rev else None)
        agents[aid] = {"st": "run" if run else ("review" if rev else "idle"),
                       "task": cur["id"] if cur else None, "pct": cur["pct"] if cur else 0, "done": done}

    all_tasks = list(tasks.values())
    return {
        "jobs": [jobs[j] for j in reversed(order)],
        "agents": agents,
        "questions": list(questions.values()),
        "feed": list(reversed(feed[-FEED_LIMIT:])),
        "kpis": {"run": sum(t["status"] == "run" for t in all_tasks),
                 "review": sum(t["status"] == "review" for t in all_tasks),
                 "done": sum(t["status"] == "done" for t in all_tasks),
                 "finds": sum(t["finds"] for t in all_tasks)},
    }
