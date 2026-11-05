import { ChatInterface } from '@/components/chat/chat-interface';
import { Dashboard } from '@/components/dashboard/dashboard';

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50 dark:bg-black">
      <Dashboard />
      <ChatInterface />
    </main>
  );
}