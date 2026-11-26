import { ChatWindow } from "../components/chat/ChatWindow";
import { SessionList } from "../components/chat/SessionList";
export default function ChatPage() { return <div className="flex h-full"><SessionList /><ChatWindow /></div>; }
