import { ChatPanel } from "@/components/chat/chat-panel";
import { PageFrame } from "@/components/ui/page-frame";

export default function ChatPage() {
  return (
    <PageFrame title="AI Chat" description="Supervisor-orchestrated multi-agent chat with streaming responses.">
      <ChatPanel />
    </PageFrame>
  );
}
