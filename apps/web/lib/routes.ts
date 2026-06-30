export type StudioRoute = {
  path: string;
  label: string;
};

export const routes: StudioRoute[] = [
  { path: "/dashboard", label: "Dashboard" },
  { path: "/chat", label: "AI Chat" },
  { path: "/agents", label: "Agent Builder" },
  { path: "/workflows", label: "Workflow Builder" },
  { path: "/marketplace", label: "Agent Marketplace" },
  { path: "/memory", label: "Memory Explorer" },
  { path: "/knowledge", label: "Knowledge Base" },
  { path: "/documents", label: "Documents" },
  { path: "/ocr", label: "OCR" },
  { path: "/vision", label: "Vision" },
  { path: "/rag", label: "RAG" },
  { path: "/sql", label: "SQL Workspace" },
  { path: "/python", label: "Python Workspace" },
  { path: "/terminal", label: "Terminal" },
  { path: "/browser", label: "Browser Automation" },
  { path: "/evaluation", label: "Evaluation" },
  { path: "/experiments", label: "Experiments" },
  { path: "/traces", label: "Langfuse Traces" },
  { path: "/logs", label: "Logs" },
  { path: "/settings", label: "Settings" },
  { path: "/models", label: "Model Manager" },
  { path: "/system", label: "System Monitoring" }
];
