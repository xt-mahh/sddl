#!/usr/bin/env python3
"""check_arch.py fixture 测试（v2.0 重构暂存区自测）

场景:
  T1 pass       合法双模块架构
  T2 fail       domain 无 owner + 多 owner
  T3 fail       越界 import（--with-imports）
  T4 fail       依赖成环
  T5 pass       single_module 豁免
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

BASE = Path(tempfile.mkdtemp(prefix="arch_fixture_"))
SCRIPT = Path(__file__).resolve().parent / "check_arch.py"


def make_spec(domain: str) -> dict:
    return {
        "meta": {"id": f"{domain}-service", "version": "0.1.0",
                 "domain": domain, "status": "frozen"},
        "decision_points": [],
        "interfaces": [], "data_models": [], "behaviors": [],
        "boundaries": [], "quality_constraints": {},
    }


def make_arch(modules, single=False, status="frozen") -> dict:
    return {
        "meta": {"id": "sys", "version": "1.0.0", "status": status,
                 "input_specs": []},
        "single_module": single,
        "modules": modules,
        "tech_stack": {},
        "directory_layout": "src/",
        "decision_points": [],
        "boundaries": [],
    }


def mod(name, owns, deps, path, resp=None):
    return {"name": name, "responsibilities": resp or ["职责"],
            "owns": owns, "depends_on": deps, "path": path}


def build_project(name, arch, domains, code=None):
    root = BASE / name
    if root.exists():
        shutil.rmtree(root)
    (root / "sddl" / "specs").mkdir(parents=True)
    (root / "sddl" / "architecture.yaml").write_text(
        yaml.dump(arch, allow_unicode=True, sort_keys=False), encoding="utf-8")
    for d in domains:
        sd = root / "sddl" / "specs" / d
        sd.mkdir()
        (sd / "spec.yaml").write_text(
            yaml.dump(make_spec(d), allow_unicode=True, sort_keys=False),
            encoding="utf-8")
    if code:
        for rel, text in code.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
    return root


def run(root, extra=()):
    r = subprocess.run([sys.executable, str(SCRIPT), str(root), "--json", *extra],
                       capture_output=True, text=True)
    return r.returncode, json.loads(r.stdout)


results = []

# T1 pass
root = build_project("t1", make_arch([
    mod("auth-gateway", ["auth"], [], "src/auth_gateway"),
    mod("payment-core", ["payment"], ["auth-gateway"], "src/payment_core"),
]), ["auth", "payment"],
    code={
        "src/auth_gateway/api.py": "def f():\n    return 1\n",
        "src/payment_core/api.py": "import auth_gateway\n\ndef g():\n    return auth_gateway.f()\n",
    })
rc, out = run(root, ["--with-imports"])
results.append(("T1 pass 双模块合法", rc == 0 and out["pass"], out))

# T2 fail: payment 无 owner + auth 双 owner
root = build_project("t2", make_arch([
    mod("auth-gateway", ["auth", "auth"], [], "src/auth_gateway"),
    mod("payment-core", [], ["auth-gateway"], "src/payment_core"),
]), ["auth", "payment"])
rc, out = run(root)
results.append(("T2 fail 无owner+多owner", rc == 1 and any(
    i["check"] == "C-arch-def1" for i in out["issues"]), out))

# T3 fail: payment 越界 import auth_gateway 但未声明依赖
root = build_project("t3", make_arch([
    mod("auth-gateway", ["auth"], [], "src/auth_gateway"),
    mod("payment-core", ["payment"], [], "src/payment_core"),
]), ["auth", "payment"],
    code={
        "src/auth_gateway/api.py": "def f():\n    return 1\n",
        "src/payment_core/api.py": "import auth_gateway\n",
    })
rc, out = run(root, ["--with-imports"])
results.append(("T3 fail 越界import", rc == 1 and any(
    i["check"] == "C-arch-def2" and "越界" in i["msg"] for i in out["issues"]), out))

# T4 fail: 依赖成环 a->b->a
root = build_project("t4", make_arch([
    mod("mod-a", ["auth"], ["mod-b"], "src/mod_a"),
    mod("mod-b", ["payment"], ["mod-a"], "src/mod_b"),
]), ["auth", "payment"])
rc, out = run(root)
results.append(("T4 fail 依赖成环", rc == 1 and any(
    "成环" in i["msg"] for i in out["issues"]), out))

# T5 pass: single_module
root = build_project("t5", make_arch([], single=True), ["only"])
rc, out = run(root)
results.append(("T5 pass single_module", rc == 0 and out["pass"], out))

# T6 pass: 并行组推导（a 独立；b,c 依赖 a；d 依赖 b）
root = build_project("t6", make_arch([
    mod("mod-a", ["auth"], [], "src/mod_a"),
    mod("mod-b", ["payment"], ["mod-a"], "src/mod_b"),
    mod("mod-c", ["billing"], ["mod-a"], "src/mod_c"),
    mod("mod-d", ["audit"], ["mod-b"], "src/mod_d"),
]), ["auth", "payment", "billing", "audit"])
rc, out = run(root)
expect = [["mod-a"], ["mod-b", "mod-c"], ["mod-d"]]
ok = rc == 0 and out["facts"].get("parallel_groups") == expect \
    and out["facts"].get("max_parallelism") == 2
results.append(("T6 pass 并行组拓扑分层", ok, out))

# T7 fail: 幽灵模块（src 下未声明目录含代码，e2e 实测漏检场景）
root = build_project("t7", make_arch([
    mod("auth-gateway", ["auth"], [], "src/auth_gateway"),
]), ["auth"],
    code={
        "src/auth_gateway/api.py": "def f():\n    return 1\n",
        "src/ghost/__init__.py": "import auth_gateway\n",
    })
rc, out = run(root, ["--with-imports"])
ok = rc == 1 and any(
    i["check"] == "C-arch-def3" and "ghost" in i["msg"] for i in out["issues"])
results.append(("T7 fail 幽灵模块目录", ok, out))

# T8 pass: 非代码资源目录不误报（src/assets 只有 txt 无 py）
root = build_project("t8", make_arch([
    mod("auth-gateway", ["auth"], [], "src/auth_gateway"),
]), ["auth"],
    code={
        "src/auth_gateway/api.py": "def f():\n    return 1\n",
        "src/assets/note.txt": "not code\n",
    })
rc, out = run(root, ["--with-imports"])
results.append(("T8 pass 资源目录不误报", rc == 0 and out["pass"], out))

# T9 fail: 模块 path 重叠/嵌套（文件归属无判据，必须显式报错）
root = build_project("t9", make_arch([
    mod("ui-shell", ["auth"], [], "src"),
    mod("auth-gateway", [], [], "src/auth_gateway"),
]), ["auth"])
rc, out = run(root, [])
ok = rc == 1 and any(
    i["check"] == "C-arch-struct" and "重叠" in i["msg"] for i in out["issues"])
results.append(("T9 fail path重叠/嵌套", ok, out))

# T10 fail: 非 Python 技术栈显式降级（JS 目录不得静默给空 import 图）
root = build_project("t10", make_arch([
    mod("web-ui", ["auth"], [], "frontend/src"),
]), ["auth"],
    code={
        "frontend/src/app.js": "import { x } from './x.js'\n",
    })
rc, out = run(root, ["--with-imports"])
ok = rc == 1 and any(
    i["check"] == "C-arch-def2" and "非 Python 技术栈" in i["msg"] for i in out["issues"])
results.append(("T10 fail 非Python显式降级", ok, out))

print(f"{'场景':<28}{'结果':<6}说明")
all_ok = True
for name, ok, out in results:
    all_ok &= ok
    msg = "OK" if ok else "FAIL: " + json.dumps(
        [i["msg"] for i in out.get("issues", [])], ensure_ascii=False)
    print(f"{name:<30}{'✅' if ok else '❌'}  {msg if not ok else ''}")
sys.exit(0 if all_ok else 1)
