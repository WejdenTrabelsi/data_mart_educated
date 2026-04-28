// Simple KPI card showing a big number with label
interface KPICardProps {
  title: string;
  value: string | number;
  color?: string;
}

export default function KPICard({ title, value, color = "bg-white" }: KPICardProps) {
  return (
    <div className={`${color} rounded-2xl shadow-lg p-6 text-center`}>
      <p className="text-gray-500 text-sm font-medium mb-2">{title}</p>
      <p className="text-4xl font-bold text-slate-800">{value}</p>
    </div>
  );
}