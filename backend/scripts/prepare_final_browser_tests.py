"""Prepare disposable browser tests with isolated output paths, preserving old evidence."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
if __name__=="__main__":
    source=ROOT/"frontend/tests";target=ROOT/"frontend/.phase10-tests"
    target.mkdir(exist_ok=False)
    transformations={"../../../phase9":"../../../phase10", "../../../work/phase8":"../../../phase10/phase8-compat", "../../../work/pdf-reports":"../../../phase10/pdf-compat"}
    records=[]
    for p in source.glob("*.ts"):
        raw=p.read_bytes();text=raw.decode("utf-8")
        for old,new in transformations.items():text=text.replace(old,new)
        dest=target/p.name;dest.write_text(text,encoding="utf-8")
        records.append({"file":p.name,"source_sha256":hashlib.sha256(raw).hexdigest(),"execution_sha256":hashlib.sha256(dest.read_bytes()).hexdigest()})
    (target/"manifest.json").write_text(json.dumps({"artifact_path_substitutions_only":transformations,"files":records},indent=2),encoding="utf-8")
    print("Prepared",len(records),"isolated test files; no application behavior substitutions.")
