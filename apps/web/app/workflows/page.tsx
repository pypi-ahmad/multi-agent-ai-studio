import { PageFrame } from "@/components/ui/page-frame";
import { WorkflowEditor } from "@/components/workflow/editor";

export default function WorkflowsPage() {
  return (
    <PageFrame title="Workflow Builder" description="Visual editor for versioned workflow JSON DSL compiled into LangGraph.">
      <WorkflowEditor />
    </PageFrame>
  );
}
