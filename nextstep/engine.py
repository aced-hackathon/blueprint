"""Code owns money, policy and execution. The language adapter only proposes."""
import json
import time
from datetime import date, timedelta
from .store import TODAY
from . import impact

ACTIONS = {"CONFIRM_GOAL": "/journey", "PREPARE_DEPOSIT": "/tasks/rental-deposit",
           "EXPLORE_CLIMATE": "/climate", "NONE": None}
SHARED_STATEMENT = "I am planning to move next month."
CHECKLIST = {"budget", "documents", "review"}

class InvalidInput(ValueError):
    pass

def require_fields(data, allowed):
    if not isinstance(data, dict) or set(data) - set(allowed):
        raise InvalidInput("Unexpected fields. Only the specified action fields are accepted.")

def monthly_totals(rows):
    """Missing months stay absent. Refunds offset outflows within their category."""
    months = {}
    for row in rows:
        month = row["date"][:7]
        categories = months.setdefault(month, {})
        categories[row["category"]] = categories.get(row["category"], 0) + row["cents"]
    return [{"month": month, "income_cents": c.get("income", 0),
             "outflow_cents": -sum(v for k, v in c.items() if k != "income"),
             "home_cents": -c.get("home", 0)} for month, c in sorted(months.items())]

def evidence_for(db, cid, prefs):
    facts = []
    climate = cid == "noah"
    if prefs["trends"]:
        rows = db.execute("SELECT * FROM transactions WHERE customer_id=? ORDER BY date", (cid,)).fetchall()
        months = monthly_totals(rows)
        baseline = [m["home_cents"] for m in months if "2026-04" <= m["month"] <= "2026-08"]
        recent = next((m for m in months if m["month"] == "2026-09"), None)
        if not climate and len(baseline) >= 3 and recent:
            average = round(sum(baseline) / len(baseline))
            increase = recent["home_cents"] - average
            if increase >= 10000:
                ratio = round(recent["home_cents"] / average, 1) if average > 0 else None
                facts.append({"evidence_id": "home-trend", "kind": "category_trend", "category": "home",
                              "baseline_cents": average, "recent_cents": recent["home_cents"],
                              "baseline_months": len(baseline), "ratio": ratio})
    if prefs["activity"]:
        event_kinds = [("lower_carbon_guide_view", "carbon-guide"), ("bike_route_preview", "bike-preview")] if climate else [("rental_guide_view", "rental-guide")]
        for kind, evidence_id in event_kinds:
            count = db.execute("SELECT COUNT(*) FROM events WHERE customer_id=? AND kind=? AND date>=?", (cid, kind, "2026-09-01")).fetchone()[0]
            if count:
                facts.append({"evidence_id": evidence_id, "kind": "app_activity", "event": kind, "count": count})
    return facts

def build_payload(facts, goal, options=None, climate=False):
    # Positive construction: no customer identifier, transaction rows or arbitrary text.
    confirmed = goal["status"] in {"confirmed", "deferred", "completed"}
    signals = [{"signal_id": "exploratory-interest", "basis_evidence_ids": [f["evidence_id"] for f in facts],
                "strength": "medium" if len(facts) > 1 else "low",
                "limitation": "Research and spending do not establish intention."}] if facts else []
    return {"purpose": "lower_carbon_options" if climate else "moving_goal_assistance",
            "observed_facts": facts, "detected_signals": signals,
            "contradictory_evidence": ([{"evidence_id": "no-confirmed-goal", "kind": "absence_of_confirmation",
                                         "finding": "No customer-confirmed goal is recorded. Browsing and spending have other explanations."}]
                                       if climate or not confirmed else []),
            "goal_confirmation_status": "unconfirmed" if climate else goal["status"],
            "approved_goal": "moving" if confirmed and not climate else None,
            "candidate_options": options or [],
            "external_context": impact.EXTERNAL_CONTEXT if climate else [],
            "allowed_action_ids": list(ACTIONS)}

class ScriptedAdapter:
    """Visible fallback only when the API key is absent or live inference fails."""
    mode = "Scripted fallback · OpenAI unavailable"
    is_remote = False

    def propose(self, payload):
        confirmed = payload["approved_goal"] == "moving"
        climate = payload["purpose"] == "lower_carbon_options"
        evidence_ids = [f["evidence_id"] for f in payload["observed_facts"]]
        return {
            "situation_hypotheses": [{"statement": "A lower-carbon routine may be of interest." if climate else "A move may be relevant.",
                                      "evidence_ids": evidence_ids, "strength": "medium" if len(evidence_ids)>1 else "low"}],
            "competing_explanations": ["The guide may be research for someone else or general curiosity."],
            "possible_whys": ["A lower-footprint trip may fit a personal goal, but motivation is unconfirmed." if climate else "A planned move could explain the signals, but the reason is unknown."],
            "customer_need": "Compare practical trip changes without assuming a climate goal." if climate else "Understand a deposit's effect on next month's cash flow.",
            "uncertainties": ["Actual travel mode and route are unverified; carbon comparisons are illustrative." if climate else "The moving goal needs customer confirmation."],
            "explanation": "If a lower-footprint routine is useful, compare the calculated bike and grocery-trip examples." if climate else "A two-month deposit estimate can make a possible move more concrete without assuming your intention.",
            "notification_wording": "You have an option you can review when you like.",
            "recommended_option_id": "BIKE_COMMUTE" if climate else "DEPOSIT_PLAN",
            "suggested_action_id": "EXPLORE_CLIMATE" if climate else "PREPARE_DEPOSIT" if confirmed else "CONFIRM_GOAL"}

def validate_proposal(proposal, payload):
    keys = {"situation_hypotheses", "competing_explanations", "possible_whys", "customer_need",
            "uncertainties", "explanation", "notification_wording", "recommended_option_id", "suggested_action_id"}
    if not isinstance(proposal, dict) or set(proposal) != keys:
        raise InvalidInput("Invalid adapter schema")
    if not isinstance(proposal["suggested_action_id"], str) or proposal["suggested_action_id"] not in ACTIONS:
        raise InvalidInput("Unapproved action")
    known = {f["evidence_id"] for f in payload["observed_facts"]}
    options = {o["id"] for o in payload["candidate_options"]}
    if not isinstance(proposal["recommended_option_id"], str) or proposal["recommended_option_id"] not in options | {"NONE"}:
        raise InvalidInput("Uncomputed option")
    if not isinstance(proposal["situation_hypotheses"], list) or len(proposal["situation_hypotheses"]) > 3:
        raise InvalidInput("Invalid hypotheses")
    for item in proposal["situation_hypotheses"]:
        if not isinstance(item, dict) or set(item) != {"statement", "evidence_ids", "strength"}:
            raise InvalidInput("Invalid hypothesis")
        if not isinstance(item["statement"], str) or len(item["statement"]) > 300 or not isinstance(item["strength"], str) or item["strength"] not in {"low", "medium", "high"}:
            raise InvalidInput("Invalid hypothesis text")
        if not isinstance(item["evidence_ids"], list) or any(not isinstance(x, str) or x not in known for x in item["evidence_ids"]):
            raise InvalidInput("Unknown evidence")
    for key in ("competing_explanations", "possible_whys", "uncertainties"):
        if not isinstance(proposal[key], list) or len(proposal[key]) > 4 or any(not isinstance(x, str) or len(x) > 320 for x in proposal[key]):
            raise InvalidInput("Invalid interpretation list")
    for key in ("customer_need", "explanation", "notification_wording"):
        if not isinstance(proposal[key], str) or len(proposal[key]) > 500:
            raise InvalidInput("Invalid explanation")
    return proposal

def answer_question(context, question, adapter):
    """A voluntary banking follow-up; it never writes the question to shared state."""
    if getattr(adapter, "is_remote", False):
        try:
            result = adapter.answer(context, question)
            if not isinstance(result, dict) or set(result) != {"answer", "uncertainty", "evidence_ids", "option_ids"}:
                raise InvalidInput("Invalid follow-up schema")
            if any(not isinstance(result[key], str) or len(result[key]) > 900 for key in ("answer", "uncertainty")):
                raise InvalidInput("Invalid follow-up text")
            known_evidence = {f["evidence_id"] for f in context["observed_facts"]}
            known_options = {o["id"] for o in context["candidate_options"]}
            for key, known in (("evidence_ids", known_evidence), ("option_ids", known_options)):
                if not isinstance(result[key], list) or any(not isinstance(x, str) or x not in known for x in result[key]):
                    raise InvalidInput("Unsupported follow-up reference")
            return {"mode": adapter.mode, **result}
        except (InvalidInput, TimeoutError, ConnectionError, TypeError, KeyError, OSError, ValueError):
            pass
    title = context["candidate_options"][0]["title"] if context["candidate_options"] else "this suggestion"
    return {"mode": "Scripted fallback · OpenAI missing or failed",
            "answer": f"The calculated option is: {title}. Review the evidence, assumptions and alternative explanations shown on this page before deciding whether it helps you.",
            "uncertainty": "This fallback does not interpret your specific question. No live model answer is available.",
            "evidence_ids": [], "option_ids": []}

def policy(goal, facts, today, climate=False):
    if climate:
        return ("SUGGEST", "EXPLORE_CLIMATE", "Illustrative lower-carbon options are ready to compare; interest remains a hypothesis.") if facts else ("NO_ACTION", "NONE", "No permitted signals support a suggestion.")
    status = goal["status"]
    if goal["suppressed"] or status in {"dismissed", "completed"}:
        return "NO_ACTION", "NONE", "Your correction is respected." if status == "dismissed" else "Your deposit preparation is complete."
    if status == "deferred" and goal["reminder_date"] and today < goal["reminder_date"]:
        return "DEFER", "NONE", "You chose later. Your plan is saved and the reminder is paused."
    if status in {"confirmed", "deferred"}:
        return "HELP_NOW", "PREPARE_DEPOSIT", "You confirmed a moving goal. A deposit plan is a useful next step."
    if facts:
        return "ASK", "CONFIRM_GOAL", "There are possible moving signals, but only you can confirm the goal."
    return "NO_ACTION", "NONE", "There is not enough permitted evidence to make a useful suggestion."

def snapshot(db, cid, today=TODAY, adapter=None):
    customer = dict(db.execute("SELECT * FROM customers WHERE id=?", (cid,)).fetchone())
    prefs = dict(db.execute("SELECT * FROM preferences WHERE customer_id=?", (cid,)).fetchone())
    goal = dict(db.execute("SELECT * FROM goals WHERE customer_id=?", (cid,)).fetchone())
    goal["checklist"] = json.loads(goal["checklist"])
    transactions = [dict(r) for r in db.execute("SELECT date,category,label,cents FROM transactions WHERE customer_id=? ORDER BY date DESC", (cid,))]
    months = monthly_totals(transactions)
    balance = customer.pop("opening_cents") + sum(t["cents"] for t in transactions)
    recent = months[-1] if months else {"income_cents": 0, "outflow_cents": 0}
    scenario_row = db.execute("SELECT * FROM travel_scenarios WHERE customer_id=?", (cid,)).fetchone()
    scenario = dict(scenario_row) if scenario_row else None
    climate = scenario is not None
    climate_options = impact.options(scenario) if scenario else []
    facts = [] if goal["suppressed"] else evidence_for(db, cid, prefs)
    decision, action, reason = policy(goal, facts, today, climate)
    deposit = goal["rent_cents"] * goal["deposit_months"]
    forecast = balance + recent["income_cents"] - recent["outflow_cents"] - deposit - goal["moving_cents"]
    options = climate_options if climate else [{"id": "DEPOSIT_PLAN", "title": "See the deposit plan",
                                                 "deposit_cents": deposit if goal["status"] in {"confirmed", "deferred"} else None,
                                                 "assumption": "Two months of estimated rent; no transaction or offer."}]
    payload = build_payload(facts, goal, options, climate) if decision in {"ASK", "HELP_NOW", "SUGGEST"} else None
    proposal = None
    elapsed = 0
    selected_adapter = adapter or ScriptedAdapter()
    adapter_status = getattr(selected_adapter, "mode", "Unknown adapter")
    if payload:
        start = time.perf_counter()
        try:
            proposal = validate_proposal(selected_adapter.propose(payload), payload)
        except (InvalidInput, TimeoutError, ConnectionError, TypeError, KeyError, OSError, json.JSONDecodeError):
            if getattr(selected_adapter, "is_remote", False):
                adapter_status = "Scripted fallback · OpenAI call failed or output invalid"
                proposal = validate_proposal(ScriptedAdapter().propose(payload), payload)
            else:
                adapter_status = "Adapter unavailable / invalid · safe fallback"
                decision, action, reason = "NO_ACTION", "NONE", "The analysis could not be validated. No suggestion was dispatched."
        elapsed = round((time.perf_counter() - start) * 1000, 2)
    journal = [dict(r) for r in db.execute("SELECT date,kind,detail FROM decisions WHERE customer_id=? ORDER BY id DESC LIMIT 15", (cid,))]
    return {"customer": customer, "today": today, "permissions": {"trends": bool(prefs["trends"]), "activity": bool(prefs["activity"]), "revision": prefs["revision"]},
            "goal": goal, "finance": {"balance_cents": balance, "income_cents": recent["income_cents"], "outflow_cents": recent["outflow_cents"], "deposit_cents": deposit, "forecast_cents": forecast, "months": months},
            "evidence": facts, "evidence_strength": "medium" if len(facts) >= 2 else "low" if facts else "none",
            "policy": {"decision": decision, "action_id": action, "route": ACTIONS[action], "reason": reason},
            "analysis": {"mode": adapter_status, "request": payload, "response": proposal, "latency_ms": elapsed, "request_persisted": False},
            "recommendations": options if decision in {"ASK", "HELP_NOW", "SUGGEST"} else [],
            "climate": {"scenario": {k: v for k, v in scenario.items() if k not in {"customer_id"}} if scenario else None,
                        "selected_option": scenario["selected_option"] if scenario else None},
            "history": journal, "transactions": transactions[:8],
            "notification": {"due": goal["status"] == "deferred" and decision == "HELP_NOW", "text": "You have a saved task ready to continue." if goal["status"] == "deferred" and decision == "HELP_NOW" else None},
            "private_mode": {"available": False, "reason": "No verified on-device model is configured. The separate sandbox is a synthetic interaction, not private AI."}}

def record(db, cid, today, kind, detail):
    db.execute("INSERT INTO decisions(customer_id,date,kind,detail) VALUES(?,?,?,?)", (cid, today, kind, detail))

def mutate(db, cid, action, data, today=TODAY):
    goal = dict(db.execute("SELECT * FROM goals WHERE customer_id=?", (cid,)).fetchone())
    if action == "confirm":
        require_fields(data, [])
        if goal["status"] != "unconfirmed":
            raise InvalidInput("Reset this scenario before confirming again.")
        db.execute("UPDATE goals SET status='confirmed',target_date='2026-10-31',suppressed=0 WHERE customer_id=?", (cid,))
        record(db, cid, today, "confirmed", "Moving goal explicitly confirmed by the customer.")
    elif action == "dismiss":
        require_fields(data, [])
        db.execute("UPDATE goals SET status='dismissed',suppressed=1,target_date=NULL,reminder_date=NULL,checklist='[]',shared_statement=NULL WHERE customer_id=?", (cid,))
        record(db, cid, today, "corrected", "Researching for a friend. Moving hypothesis withdrawn; further moving suggestions suppressed.")
    elif action == "defer":
        require_fields(data, [])
        if goal["status"] != "confirmed":
            raise InvalidInput("Confirm the goal before deferring it.")
        reminder = (date.fromisoformat(today) + timedelta(days=7)).isoformat()
        db.execute("UPDATE goals SET status='deferred',reminder_date=? WHERE customer_id=?", (reminder, cid))
        record(db, cid, today, "deferred", f"Customer requested a reminder on {reminder}. No immediate notification.")
    elif action == "resume":
        require_fields(data, [])
        if goal["status"] != "deferred":
            raise InvalidInput("No deferred goal to resume.")
        db.execute("UPDATE goals SET status='confirmed',reminder_date=NULL WHERE customer_id=?", (cid,))
        record(db, cid, today, "resumed", "Customer resumed the saved plan.")
    elif action == "permissions":
        require_fields(data, ["trends", "activity"])
        if set(data) != {"trends", "activity"} or any(type(v) is not bool for v in data.values()):
            raise InvalidInput("Both permissions must be boolean values.")
        db.execute("UPDATE preferences SET trends=?,activity=?,revision=revision+1 WHERE customer_id=?", (data["trends"], data["activity"], cid))
        record(db, cid, today, "permissions", "Personalization permissions updated. Derived analysis is recomputed from permitted fields.")
    elif action == "budget":
        require_fields(data, ["rent_cents", "deposit_months", "moving_cents"])
        if goal["status"] != "confirmed":
            raise InvalidInput("An active confirmed goal is required.")
        limits = {"rent_cents": (10000, 1000000), "deposit_months": (1, 3), "moving_cents": (0, 500000)}
        if set(data) != set(limits) or any(type(data[k]) is not int or not lo <= data[k] <= hi for k, (lo, hi) in limits.items()):
            raise InvalidInput("Enter valid whole-cent estimates within the displayed limits.")
        db.execute("UPDATE goals SET rent_cents=?,deposit_months=?,moving_cents=?,checklist='[]' WHERE customer_id=?", (data["rent_cents"], data["deposit_months"], data["moving_cents"], cid))
        record(db, cid, today, "budget", "Deposit estimate updated; preparation checklist reset for review.")
    elif action == "checklist":
        require_fields(data, ["items"])
        items = data.get("items")
        if goal["status"] != "confirmed" or not isinstance(items, list) or any(not isinstance(x, str) or x not in CHECKLIST for x in items) or len(set(items)) != len(items):
            raise InvalidInput("Only the fixed checklist of an active plan can be updated.")
        db.execute("UPDATE goals SET checklist=? WHERE customer_id=?", (json.dumps(items), cid))
    elif action == "complete":
        require_fields(data, [])
        if goal["status"] != "confirmed" or set(json.loads(goal["checklist"])) != CHECKLIST:
            raise InvalidInput("Finish all three preparation steps first.")
        db.execute("UPDATE goals SET status='completed',reminder_date=NULL WHERE customer_id=?", (cid,))
        record(db, cid, today, "completed", "Mock deposit preparation completed. No money moved and no bank account opened.")
    elif action == "share":
        require_fields(data, ["statement", "purpose"])
        if data != {"statement": SHARED_STATEMENT, "purpose": "moving_goal_assistance"}:
            raise InvalidInput("Only the exact previewed moving statement can be shared.")
        db.execute("UPDATE goals SET status='confirmed',target_date='2026-10-31',suppressed=0,reminder_date=NULL,shared_statement=?,checklist='[]' WHERE customer_id=?", (SHARED_STATEMENT, cid))
        record(db, cid, today, "shared", "Customer approved this statement for moving assistance: " + SHARED_STATEMENT)
    elif action == "save-climate":
        require_fields(data, ["option_id"])
        if set(data) != {"option_id"} or not isinstance(data["option_id"], str) or data["option_id"] not in {"BIKE_COMMUTE", "NEARBY_GROCERY"}:
            raise InvalidInput("Only a calculated climate scenario can be saved.")
        if not db.execute("SELECT 1 FROM travel_scenarios WHERE customer_id=?", (cid,)).fetchone():
            raise InvalidInput("No climate scenario for this customer.")
        db.execute("UPDATE travel_scenarios SET selected_option=? WHERE customer_id=?", (data["option_id"], cid))
        record(db, cid, today, "saved-option", "Customer saved an illustrative trip option; no journey, purchase or notification was booked.")
    else:
        raise InvalidInput("This action is not in the server allowlist.")
