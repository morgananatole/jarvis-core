"""Validação offline da fila de agentes; não executa modelos nem tarefas externas."""
import json
from pathlib import Path

CONFIG = Path(__file__).resolve().parent / "toolkit" / "shipyard.v1.json"


def validate_queue(path=CONFIG):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    tasks = data["queue"]
    roles = {role["id"] for role in data["roles"]}
    ids = {task["id"] for task in tasks}
    if len(ids) != len(tasks):
        raise ValueError("duplicate_task_id")
    for task in tasks:
        if task["role"] not in roles:
            raise ValueError("unknown_role")
        if task["id"] in task["dependencies"]:
            raise ValueError("self_dependency")
        if any(dep not in ids for dep in task["dependencies"]):
            raise ValueError("unknown_dependency")
        if task["status"] not in data["task_contract"]["states"]:
            raise ValueError("invalid_state")
    return {"valid": True, "tasks": len(tasks), "active_workers": 0}


if __name__ == "__main__":
    print(json.dumps(validate_queue()))
