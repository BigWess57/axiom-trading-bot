import TokenSOL from '@web3icons/react/icons/tokens/TokenSOL';

function StatCard({ title, value, valueColor = "text-white", isSol = false }: { title: string, value: string, valueColor?: string, isSol?: boolean }) {
  return (
    <div className="bg-gray-900/40 backdrop-blur border border-gray-800 rounded-xl p-6">
      <p className="text-gray-400 text-sm font-medium mb-1">{title}</p>
      <div className={`text-2xl font-bold ${valueColor} flex items-center gap-2`}>
        {value}
        {isSol && <TokenSOL variant="branded" size={28} className="shrink-0" />}
      </div>
    </div>
  );
}

export default StatCard;
