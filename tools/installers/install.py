import os

d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d:
        break
    d = p
BASE = d
print("ROOT: " + BASE)

removed = []
for rel in ("_diag_changelog.txt", os.path.join("tools", "diag_changelog.py")):
    p = os.path.join(BASE, rel)
    if os.path.exists(p):
        os.remove(p)
        removed.append(rel.replace("\\", "/"))
print("REMOVED: " + (", ".join(removed) or "none"))

gi = os.path.join(BASE, ".gitignore")
lines = open(gi, encoding="utf-8").read().splitlines() if os.path.exists(gi) else []
add = []
for pat in ("_diag_*.txt", "tools/diag_*.py"):
    if pat not in lines:
        lines.append(pat)
        add.append(pat)
if add:
    open(gi, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("GITIGNORE ADDED: " + (", ".join(add) or "none"))

print("=" * 60)
print("MARKER_END: diag junk removed + ignore patterns")
print("=" * 60)
print("Commit + Push:")
print("  .gitignore")
print("  tools/installers/install.py")
print("  deletions: _diag_changelog.txt, tools/diag_changelog.py")