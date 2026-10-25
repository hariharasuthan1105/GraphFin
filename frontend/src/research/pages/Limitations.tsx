import { useResearch } from "../state";
import type { Limitations as Data } from "../contract";
import { State, Heading, Panel, Notice } from "../ui";
export default function Limitations() {
  const r = useResearch<Data>("/limitations", "Limitations");
  return (
    <>
      <Heading index="08" title="Research limitations">
        A complete evidence record includes uncertainty, negative results and
        unfinished work.
      </Heading>
      <Notice>
        IBM AML: upstream account-label lineage partially verified. PaySim:
        conflicting label provenance unresolved. CREST: superior detection and
        explanation quality unsupported. Phase 5: full intervention-based E6
        benchmark incomplete. Transfer interpretation depends on dataset and
        ground-truth provenance.
      </Notice>
      {!r.data ? (
        <State {...r} />
      ) : (
        r.data.items.map((x) => (
          <Panel key={x.topic} title={x.topic} tag={x.assessment}>
            <div className="panel-body">
              <p>{x.description}</p>
            </div>
          </Panel>
        ))
      )}
      <Panel title="Read the status precisely">
        <div className="panel-body">
          <p>
            Completed refers to execution. Reproducible refers to repeated
            outputs on the same inputs. Verified refers to authenticated
            artifact bytes. None establishes ground-truth validity. Exploratory
            diagnostics describe model sensitivity; unsupported conclusions
            remain unsupported.
          </p>
        </div>
      </Panel>
    </>
  );
}
