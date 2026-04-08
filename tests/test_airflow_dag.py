import runpy
import sys
import types
from pathlib import Path
from typing import Any, cast


class FakeTaskNode:
    def __init__(self, task_id: str, bash_command: str | None = None):
        self.task_id = task_id
        self.bash_command = bash_command

    def __rshift__(self, other):
        return other


class FakeDAG:
    def __init__(self, *args, **kwargs):
        self.dag_id = kwargs.get("dag_id")
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def fake_task(func=None, **_kwargs):
    def decorator(inner):
        def wrapper(*args, **kwargs):
            return FakeTaskNode(task_id=inner.__name__)

        return wrapper

    return decorator(func) if func is not None else decorator


class FakeBashOperator(FakeTaskNode):
    def __init__(self, task_id: str, bash_command: str):
        super().__init__(task_id=task_id, bash_command=bash_command)


def test_airflow_dag_import_smoke(monkeypatch):
    airflow_module = types.ModuleType("airflow")
    cast(Any, airflow_module).DAG = FakeDAG

    decorators_module = types.ModuleType("airflow.decorators")
    cast(Any, decorators_module).task = fake_task

    operators_module = types.ModuleType("airflow.operators")
    bash_module = types.ModuleType("airflow.operators.bash")
    cast(Any, bash_module).BashOperator = FakeBashOperator

    monkeypatch.setitem(sys.modules, "airflow", airflow_module)
    monkeypatch.setitem(sys.modules, "airflow.decorators", decorators_module)
    monkeypatch.setitem(sys.modules, "airflow.operators", operators_module)
    monkeypatch.setitem(sys.modules, "airflow.operators.bash", bash_module)

    dag_file = Path(__file__).resolve().parents[1] / "airflow" / "dags" / "vertexops_ingest.py"
    namespace = runpy.run_path(str(dag_file))

    dag = namespace["dag"]
    dbt_run = namespace["dbt_run"]
    vertex_train = namespace["vertex_train"]

    assert dag.dag_id == "vertexops_ingest_resume_screening"
    assert "dbt build" in dbt_run.bash_command
    assert "vertex_launcher.py" in vertex_train.bash_command
