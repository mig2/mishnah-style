"""Shared helpers for the entities-KB test suite (stdlib unittest, no new deps)."""

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
ENTITIES = REPO / "entities"
DATA = ENTITIES / "data"
SCHEMA = ENTITIES / "schema"
FIXTURES = ENTITIES / "fixtures"
MASECHOT = REPO / "masechot"

# make `import kb_lib` work
sys.path.insert(0, str(SCRIPTS))


def load_script(modname, filename):
    """Import a (possibly hyphenated) script as a module."""
    spec = importlib.util.spec_from_file_location(modname, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_yaml(path):
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_registry(schema_dir=SCHEMA):
    """Build a referencing registry from all schemas, keyed by $id."""
    from referencing import Registry, Resource
    reg = Registry()
    schemas = {}
    for p in sorted(Path(schema_dir).glob("*.schema.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        schemas[p.name] = s
        reg = reg.with_resource(s["$id"], Resource.from_contents(s))
    return reg, schemas


def validator_for(name):
    """A Draft 2020-12 validator for the named schema (e.g. 'person', 'claim')."""
    from jsonschema import Draft202012Validator
    reg, schemas = load_registry()
    return Draft202012Validator(schemas[f"{name}.schema.json"], registry=reg)


def is_valid(name, instance):
    return not list(validator_for(name).iter_errors(instance))


def masechot_slugs():
    return {p.stem for p in MASECHOT.glob("*.html") if p.stem != "index"}


def sedarim_slugs():
    data = load_yaml(DATA / "vocab" / "sedarim.yaml")
    return {m["slug"] for masechtot in data.values() for m in masechtot}
