import json, datetime
from modules.tables.models import TableAccess, TableRow

TRASH_DAYS = 30

def jload(s, d):
    try:
        v = json.loads(s)
        return v if v is not None else d
    except Exception:
        return d

def num(v):
    v = str(v if v is not None else "").replace(" ", "").replace(",", ".")
    try:
        return float(v)
    except Exception:
        return None

def dparse(v):
    v = str(v or "").strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%Y %H:%M", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(v, fmt)
        except Exception:
            pass
    return None

def fnum(x):
    if x is None:
        return ""
    if x == int(x):
        return str(int(x))
    return str(round(x, 2))

def resolve_token(tok, data):
    tok = (tok or "").strip()
    if tok in data:
        return str(data.get(tok, "") or "")
    return tok

def compute_value(col, data, remote):
    f = jload(col.formula, {}) or {}
    kind = f.get("kind")
    try:
        if col.col_type == "ref":
            want = str(data.get(f.get("match_local"), "") or "")
            if not want:
                return ""
            for rd in remote(int(f.get("ref_table") or 0)):
                if str(rd.get(f.get("match_remote"), "") or "") == want:
                    return str(rd.get(f.get("show"), "") or "")
            return ""
        if kind == "arith":
            a = num(resolve_token(f.get("a"), data))
            b = num(resolve_token(f.get("b"), data))
            if a is None or b is None:
                return ""
            op = f.get("op")
            if op == "add": r = a + b
            elif op == "sub": r = a - b
            elif op == "mul": r = a * b
            elif op == "div":
                if b == 0: return ""
                r = a / b
            else: return ""
            return fnum(r)
        if kind == "concat":
            return (resolve_token(f.get("a"), data) + " " + resolve_token(f.get("b"), data)).strip()
        if kind == "days":
            a = dparse(resolve_token(f.get("a"), data))
            btok = (f.get("b") or "").strip()
            b = dparse(resolve_token(btok, data)) if btok else datetime.datetime.utcnow()
            if a is None or b is None:
                return ""
            return str((a - b).days)
        if kind == "if":
            base = str(data.get(f.get("col"), "") or "")
            val = str(f.get("value") or "")
            op = f.get("op")
            na, nv = num(base), num(val)
            if op == "eq": ok = base == val
            elif op == "ne": ok = base != val
            elif op == "contains": ok = val in base
            elif op == "gt": ok = (na is not None and nv is not None and na > nv)
            elif op == "lt": ok = (na is not None and nv is not None and na < nv)
            else: ok = False
            return str(f.get("then") if ok else f.get("else") or "")
    except Exception:
        return ""
    return ""

def role_access(tid, role_id):
    m = {"view": False, "create": False, "delete": False, "edit": set()}
    for a in TableAccess.query.filter_by(table_id=tid, role_id=role_id).all():
        if a.column_key == "*":
            if a.mode in ("view", "create", "delete"):
                m[a.mode] = True
        else:
            m["edit"].add(a.column_key)
    return m

def user_access(tid, user):
    m = {"view": False, "create": False, "delete": False, "edit": set()}
    if user is None or not user.is_authenticated:
        return m
    if user.is_superuser:
        m["view"] = m["create"] = m["delete"] = True
        m["edit"] = None
        return m
    return role_access(tid, user.role_id)

def can_edit_col(m, colkey):
    return m["edit"] is None or colkey in m["edit"]

def calc_counters(t, datas):
    out = []
    for c in jload(t.counters, []):
        wcol = c.get("wcol"); wval = c.get("wval")
        sel = [d for d in datas if (not wcol) or str(d.get(wcol, "") or "") == str(wval or "")]
        if c.get("func") == "count":
            val = str(len(sel))
        else:
            s = 0.0
            for d in sel:
                n = num(d.get(c.get("col")))
                if n is not None:
                    s += n
            val = fnum(s)
        out.append({"title": c.get("title", ""), "value": val})
    return out
