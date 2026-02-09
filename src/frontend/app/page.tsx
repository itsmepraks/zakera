import ChatInterface from './components/ChatInterface'

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4 bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="w-full max-w-6xl">
        <div className="text-center mb-8">
          <h1 className="text-5xl font-bold text-gray-900 mb-3">
            Zakera AI
          </h1>
          <p className="text-xl text-gray-600">
            Your intelligent conversation partner
          </p>
        </div>
        <ChatInterface />
      </div>
    </main>
  )
}
