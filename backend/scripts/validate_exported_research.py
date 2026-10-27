import json
import os

with open("frontend/src/research/contract.schema.json", "r", encoding="utf-8") as f:
    schemas = json.load(f)

def validate(value, schema, registry=schemas):
    if not schema:
        return False
    if "const" in schema and value != schema["const"]:
        return False
    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        return validate(value, registry[ref_name], registry)
    if "anyOf" in schema:
        return any(validate(value, s, registry) for s in schema["anyOf"])
    if "enum" in schema and value not in schema["enum"]:
        return False
    if schema.get("type") == "null":
        return value is None
    if schema.get("type") == "array":
        return isinstance(value, list) and len(value) <= 1000 and all(validate(v, schema.get("items", {}), registry) for v in value)
    if schema.get("type") == "object":
        if not isinstance(value, dict):
            return False
        req = schema.get("required", [])
        if not all(k in value for k in req):
            return False
        props = schema.get("properties", {})
        return all(k not in value or validate(value[k], s, registry) for k, s in props.items())
    if schema.get("type") in ("number", "integer"):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True

base_dir = "frontend/public/data/research"
tests = [
  ("Overview", "overview.json"),
  ("Page_Dataset_", "datasets.json"),
  ("Dataset", "datasets/ibm-5k.json"),
  ("Dataset", "datasets/ibm-50k.json"),
  ("Dataset", "datasets/paysim.json"),
  ("Page_Experiment_", "experiments.json"),
  ("ModelSeeds", "model-seeds.json"),
  ("Reproducibility", "reproducibility.json"),
  ("Limitations", "limitations.json"),
  ("Page_Diagnostic_", "diagnostics.json")
]

all_valid = True
for sKey, fName in tests:
    with open(os.path.join(base_dir, fName), "r", encoding="utf-8") as f:
        data = json.load(f)
    ok = validate(data, schemas[sKey])
    print(f"{sKey} ({fName}) => Valid? {ok}")
    if not ok:
        all_valid = False

print("All valid:", all_valid)
