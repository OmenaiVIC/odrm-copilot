import { Dashboard } from '@/components/dashboard/dashboard';
import { ChatInterface } from '@/components/chat/chat-interface';
import { AuthGate } from '@/components/auth/auth-gate';

export default function Home() {
  return (
    <AuthGate>
      <main className="min-h-screen bg-gray-50 dark:bg-black pb-20">
        <Dashboard />
        <div className="max-w-7xl mx-auto p-4 md:p-8">
          <ChatInterface />
        </div>
      </main>
    </AuthGate>
  );
}