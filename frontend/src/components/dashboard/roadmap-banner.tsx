'use client';

export function RoadmapBanner() {
  return (
    <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50/50 p-6 dark:border-zinc-700 dark:bg-zinc-900/30">
      <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-2">
        🚀 Coming Soon: Operational Intelligence
      </h3>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
        The following features are currently in development and will be unlocked during the NUPRC Pilot phase.
      </p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-lg border border-gray-200 bg-white p-4 opacity-60 dark:border-zinc-800 dark:bg-zinc-950">
          <span className="inline-flex items-center rounded-md bg-yellow-50 px-2 py-1 text-xs font-medium text-yellow-800 ring-1 ring-inset ring-yellow-600/20 mb-2">
            Sprint 8 (Pilot)
          </span>
          <h4 className="font-medium text-gray-900 dark:text-white">Predictive Maintenance</h4>
          <p className="text-xs text-gray-500 mt-1">
            Train on real-world plant data to predict equipment degradation, prevent costly shutdowns, and automatically alert operators to dangerous carbon buildup.
          </p>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-4 opacity-60 dark:border-zinc-800 dark:bg-zinc-950">
          <span className="inline-flex items-center rounded-md bg-yellow-50 px-2 py-1 text-xs font-medium text-yellow-800 ring-1 ring-inset ring-yellow-600/20 mb-2">
            Sprint 9 (Pilot)
          </span>
          <h4 className="font-medium text-gray-900 dark:text-white">Tamper-Proof Carbon Credits</h4>
          <p className="text-xs text-gray-500 mt-1">
            Upgrade to a secure, blockchain-style audit trail. This prevents data tampering and makes your carbon credits fully bankable and verified by international ESG investors.
          </p>
        </div>
      </div>
    </div>
  );
}