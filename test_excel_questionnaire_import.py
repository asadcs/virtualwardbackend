from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict, Counter

import openpyxl
from fastapi.testclient import TestClient

from main import app
from db import Base, engine, SessionLocal
from role import Role

client = TestClient(app)

# =========================
# CONFIG
# =========================
EXCEL_FILENAME = "scoring system4.xlsx"  # keep this file at repo root

ADMIN = {"name": "Admin", "email": "excel_admin@gmail.com", "password": "12345678"}

STATE = {"admin": {"id": None, "verify": None, "access": None}}

# =========================
# DB RESET
# =========================
def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

# =========================
# HELPERS (auth + db)
# =========================
def _db():
    return SessionLocal()

def _create_role_direct(name: str) -> int:
    db = _db()
    try:
        existing = db.query(Role).filter(Role.name == name).first()
        if existing:
            return existing.id
        role = Role(name=name)
        db.add(role)
        db.commit()
        db.refresh(role)
        return role.id
    finally:
        db.close()

def _register_admin():
    r = client.post("/users/register", json={
        "name": ADMIN["name"],
        "email": ADMIN["email"],
        "password": ADMIN["password"],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    STATE["admin"]["id"] = body["user_id"]
    STATE["admin"]["verify"] = body["dev_email_verification_token"]

def _verify_admin():
    r = client.post("/users/verify-email", json={"token": STATE["admin"]["verify"]})
    assert r.status_code == 200, r.text

def _login_admin():
    r = client.post("/users/login", json={
        "email": ADMIN["email"],
        "password": ADMIN["password"],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    STATE["admin"]["access"] = body["access_token"]

def _auth_headers():
    return {"Authorization": f"Bearer {STATE['admin']['access']}"}

def _assign_admin_role():
    admin_role_id = _create_role_direct("ADMIN")
    r = client.post("/users/assign-role", json={
        "user_id": STATE["admin"]["id"],
        "role_id": admin_role_id,
    })
    assert r.status_code == 200, r.text

# =========================
# EXCEL → FLOW PAYLOAD (your rules)
# =========================
def _norm_sev(x: Any) -> str:
    # User rule: blank rag => GREEN
    if x is None:
        return "GREEN"
    s = str(x).strip().lower()
    if s in ("green", "g"):
        return "GREEN"
    if s in ("amber", "ambar", "am", "a"):
        return "AMBER"
    if s in ("red", "r"):
        return "RED"
    # unknown => GREEN
    return "GREEN"

def _sev_from_points(points: int) -> str:
    # same thresholds you use in UI
    if points >= 100:
        return "RED"
    if points >= 30:
        return "AMBER"
    return "GREEN"

def _sheet_rows(ws):
    return [list(r) for r in ws.iter_rows(values_only=True)]

def _load_excel(path: str):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws_symptoms = wb["Colorectal symptoms and signs"]
    ws_clinical = wb["Clincial Obs- Colorectal"]
    return _sheet_rows(ws_symptoms), _sheet_rows(ws_clinical)

def _build_flow_payload_from_excel(excel_path: str) -> Dict[str, Any]:
    rows1, rows2 = _load_excel(excel_path)

    # -----------------------
    # Sheet 1 (Category 2)
    # -----------------------
    # header row pattern:
    # [None, 'Question', 'Response', None, 'Next Question/ Alert', 'RAG']
    data1 = []
    current_key = None
    current_question = None

    # start at row 2 (0-indexed) because first 2 rows are title+headers
    for r in rows1[2:]:
        key = r[0] if r[0] is not None else None
        q = r[1] if r[1] is not None else None
        resp = r[2]
        nxt = r[4]
        rag = r[5]

        if key:
            current_key = str(key).strip()
            current_question = q

        if current_key is None:
            continue

        # keep rows that have anything meaningful (resp OR next OR rag)
        if resp is None and nxt is None and rag is None and current_question is None:
            continue

        data1.append((current_key, current_question, resp, nxt, rag))

    key_info = defaultdict(lambda: {"question": None, "rows": []})
    for k, q, resp, nxt, rag in data1:
        if key_info[k]["question"] is None and q is not None:
            key_info[k]["question"] = str(q).strip()
        key_info[k]["rows"].append((resp, nxt, rag))

    # -----------------------
    # Sheet 2 (Category 1)
    # -----------------------
    # header row:
    # ['Number','Shown or Hidden?','Question','Answer','NEWS 2 score','Seriousness Points','Next Question']
    data2 = []
    current_num = None
    current_question = None
    current_shown = None

    # start at row 3 (0-indexed) where data begins in your file
    for r in rows2[3:]:
        num = r[0]
        shown = r[1]
        q = r[2]
        ans = r[3]
        news2 = r[4]
        pts = r[5]
        nxt = r[6]

        if num is not None:
            current_num = str(num).strip()
            current_question = q
            current_shown = shown

        if current_num is None:
            continue

        data2.append((current_num, current_shown, current_question, ans, news2, pts, nxt))

    info2 = defaultdict(lambda: {"shown": None, "question": None, "rows": []})
    for num, shown, q, ans, news2, pts, nxt in data2:
        if info2[num]["shown"] is None and shown is not None:
            info2[num]["shown"] = str(shown).strip()
        if info2[num]["question"] is None and q is not None:
            info2[num]["question"] = str(q).strip()
        info2[num]["rows"].append((ans, news2, pts, nxt))

    # -----------------------
    # Key normalization for next links (case-insensitive)
    # -----------------------
    all_node_keys = set(key_info.keys()) | set(info2.keys())
    lower_map = {k.lower(): k for k in all_node_keys}

    def norm_next(nxt: Any) -> str:
        # user rule: missing next -> END
        if nxt is None:
            return "END"
        s = str(nxt).strip()
        if s == "" or s.lower() == "end":
            return "END"
        return lower_map.get(s.lower(), s)

    # -----------------------
    # Build nodes payload
    # -----------------------
    nodes: List[Dict[str, Any]] = []

    # Category 1 nodes (clinical)
    # MESSAGE nodes auto_next from first non-null next found
    auto_next_msg_cat1 = {}
    for k, v in info2.items():
        if v["shown"] and v["shown"].lower() == "hidden":
            nxt = None
            for ans, news2, pts, nx in v["rows"]:
                if nx is not None:
                    nxt = nx
                    break
            auto_next_msg_cat1[k] = norm_next(nxt)

    # Add cat1 nodes
    for k, v in info2.items():
        shown = (v["shown"] or "").strip().lower()
        qtext = v["question"] or "dummy"
        if shown == "hidden":
            # MESSAGE node
            nodes.append({
                "node_key": k,
                "node_type": "MESSAGE",
                "category": 1,
                "title": None,
                "body_text": qtext,
                "help_text": None,
                "parent_node_key": None,
                "depth_level": 0,
                "default_next_node_key": None,
                "auto_next_node_key": auto_next_msg_cat1.get(k, "END"),
                "ui_ack_required": True,
                "alert_severity": None,
                "notify_admin": False,
                "options": [],
            })
        else:
            # QUESTION node
            ans_rows = [r for r in v["rows"] if r[0] is not None]
            options = []
            for i, (ans, news2, pts, nxt) in enumerate(ans_rows, start=1):
                label = str(ans).strip() if ans is not None else "dummy"
                n2 = int(news2) if news2 is not None else 0
                p = int(pts) if pts is not None else 0
                options.append({
                    "display_order": i,
                    "label": label if label else "dummy",
                    "value": f"{k}_opt{i}",
                    "severity": _sev_from_points(p),
                    "news2_score": n2,
                    "seriousness_points": p,
                    "next_node_key": norm_next(nxt),
                })

            # If QUESTION has < 2 options, fill with dummy (user instruction)
            if len(options) < 2:
                options.append({
                    "display_order": len(options) + 1,
                    "label": "dummy",
                    "value": f"{k}_opt{len(options) + 1}",
                    "severity": "GREEN",
                    "news2_score": 0,
                    "seriousness_points": 0,
                    "next_node_key": "END",
                })

            nodes.append({
                "node_key": k,
                "node_type": "QUESTION",
                "category": 1,
                "title": None,
                "body_text": qtext,
                "help_text": None,
                "parent_node_key": None,
                "depth_level": 0,
                "default_next_node_key": None,
                "auto_next_node_key": None,
                "ui_ack_required": False,
                "alert_severity": None,
                "notify_admin": False,
                "options": options,
            })

    # Category 2 nodes (symptoms)
    def first_next_for_key(k: str) -> str:
        for resp, nxt, rag in key_info[k]["rows"]:
            if nxt is not None and str(nxt).strip() != "":
                return norm_next(nxt)
        # user rule: missing next -> END
        return "END"

    for k, v in key_info.items():
        qtext = v["question"] or "dummy"

        if k.lower().startswith("instruction"):
            # MESSAGE
            nodes.append({
                "node_key": k,
                "node_type": "MESSAGE",
                "category": 2,
                "title": None,
                "body_text": qtext,
                "help_text": None,
                "parent_node_key": None,
                "depth_level": 0,
                "default_next_node_key": None,
                "auto_next_node_key": first_next_for_key(k),
                "ui_ack_required": True,
                "alert_severity": None,
                "notify_admin": False,
                "options": [],
            })
            continue

        if k.lower().startswith("alert"):
            # ALERT
            nodes.append({
                "node_key": k,
                "node_type": "ALERT",
                "category": 2,
                "title": None,
                "body_text": qtext,
                "help_text": None,
                "parent_node_key": None,
                "depth_level": 0,
                "default_next_node_key": None,
                "auto_next_node_key": first_next_for_key(k),  # user: missing -> END
                "ui_ack_required": True,
                "alert_severity": _norm_sev(None),  # user: blank => GREEN
                "notify_admin": False,
                "options": [],
            })
            continue

        # QUESTION
        ans_rows = []
        for resp, nxt, rag in v["rows"]:
            # keep option row if anything exists; if response missing => dummy
            if resp is not None or nxt is not None or rag is not None:
                ans_rows.append((resp, nxt, rag))

        options = []
        for i, (resp, nxt, rag) in enumerate(ans_rows, start=1):
            label = str(resp).strip() if resp is not None else "dummy"
            if not label:
                label = "dummy"
            options.append({
                "display_order": i,
                "label": label,
                "value": f"{k}_opt{i}",
                "severity": _norm_sev(rag),  # user: blank => GREEN
                "news2_score": 0,
                "seriousness_points": 0,
                "next_node_key": norm_next(nxt),  # user: missing => END
            })

        # If QUESTION has < 2 options, fill dummy
        if len(options) < 2:
            options.append({
                "display_order": len(options) + 1,
                "label": "dummy",
                "value": f"{k}_opt{len(options) + 1}",
                "severity": "GREEN",
                "news2_score": 0,
                "seriousness_points": 0,
                "next_node_key": "END",
            })

        nodes.append({
            "node_key": k,
            "node_type": "QUESTION",
            "category": 2,
            "title": None,
            "body_text": qtext,
            "help_text": None,
            "parent_node_key": None,
            "depth_level": 0,
            "default_next_node_key": None,
            "auto_next_node_key": None,
            "ui_ack_required": False,
            "alert_severity": None,
            "notify_admin": False,
            "options": options,
        })

    # choose a safe start node
    start_node_key = "Q1" if any(n["node_key"] == "Q1" for n in nodes) else nodes[0]["node_key"]

    return {
        "name": "Excel Imported Flow (Test)",
        "description": "Generated from scoring system4.xlsx",
        "flow_type": "EXCEL_IMPORT_TEST",
        "status": "DRAFT",
        "start_node_key": start_node_key,
        "nodes": nodes,
    }

# =========================
# EXPECTATION BUILDERS
# =========================
def _index_flow(flow_detail: Dict[str, Any]):
    node_by_key = {n["node_key"]: n for n in flow_detail["nodes"]}
    opt_by_node = {}
    for n in flow_detail["nodes"]:
        if n["node_type"] == "QUESTION":
            opt_by_node[n["node_key"]] = {(o["display_order"], o["label"], o["next_node_key"], o["severity"], o["news2_score"], o["seriousness_points"]) for o in n.get("options", [])}
        else:
            opt_by_node[n["node_key"]] = set()
    return node_by_key, opt_by_node

# =========================
# TESTS
# =========================
def test_00_admin_bootstrap():
    _register_admin()
    _verify_admin()
    _login_admin()
    _assign_admin_role()

def test_01_import_excel_create_flow_and_assert_everything_present():
    excel_path = os.path.join(os.getcwd(), EXCEL_FILENAME)
    assert os.path.exists(excel_path), f"Excel file not found at: {excel_path}"

    payload = _build_flow_payload_from_excel(excel_path)

    # 1) create flow
    r = client.post("/flows/", json=payload, headers=_auth_headers())
    assert r.status_code == 200, r.text
    flow_id = r.json()["flow_id"]

    # 2) fetch flow detail
    r = client.get(f"/flows/{flow_id}", headers=_auth_headers())
    assert r.status_code == 200, r.text
    flow = r.json()

    # 3) validate endpoint must pass
    r = client.get(f"/flows/{flow_id}/validate", headers=_auth_headers())
    assert r.status_code == 200, r.text
    v = r.json()
    assert v["valid"] is True, f"Flow validation failed: {v.get('errors')}"

    # 4) Deep equality checks (node presence + option presence)
    expected_nodes = {n["node_key"]: n for n in payload["nodes"]}
    actual_nodes = {n["node_key"]: n for n in flow["nodes"]}

    # Every expected node exists
    assert set(expected_nodes.keys()) == set(actual_nodes.keys()), (
        "Node keys mismatch.\n"
        f"Missing in API: {set(expected_nodes.keys()) - set(actual_nodes.keys())}\n"
        f"Extra in API: {set(actual_nodes.keys()) - set(expected_nodes.keys())}"
    )

    # Check each node + options
    for key, exp in expected_nodes.items():
        act = actual_nodes[key]

        assert act["node_type"] == exp["node_type"]
        assert act["category"] == exp["category"]

        # body_text must exist (dummy allowed)
        assert act["body_text"] is not None and str(act["body_text"]).strip() != ""

        if exp["node_type"] == "QUESTION":
            exp_opts = exp.get("options", [])
            act_opts = act.get("options", [])

            # must have exact count
            assert len(act_opts) == len(exp_opts), f"Option count mismatch at node {key}"

            # must match all key option fields
            exp_set = {(o["display_order"], o["label"], o["next_node_key"], o["severity"], o["news2_score"], o["seriousness_points"]) for o in exp_opts}
            act_set = {(o["display_order"], o["label"], o["next_node_key"], o["severity"], o["news2_score"], o["seriousness_points"]) for o in act_opts}
            assert act_set == exp_set, f"Options mismatch at node {key}"

            # also assert nothing missing per your rules
            for o in act_opts:
                assert o["label"] and str(o["label"]).strip() != ""
                assert o["severity"] in ("GREEN", "AMBER", "RED")
                assert o["next_node_key"] and str(o["next_node_key"]).strip() != ""

        else:
            # MESSAGE/ALERT must have no options
            assert (act.get("options") or []) == [], f"Non-question node {key} must not have options"

            # Missing alert next => END rule is enforced by payload builder
            if exp["node_type"] in ("MESSAGE", "ALERT"):
                assert act.get("auto_next_node_key") is not None
                assert str(act["auto_next_node_key"]).strip() != ""

            if exp["node_type"] == "ALERT":
                assert act.get("alert_severity") in ("GREEN", "AMBER", "RED")
