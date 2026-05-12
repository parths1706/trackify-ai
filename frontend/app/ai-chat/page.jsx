"use client";

import ChatWindow from "./components/ChatWindow";

export default function AiChatPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-6xl">
        <ChatWindow />
      </div>
    </div>
  );
}
