import { BarChart3, Layers, DollarSign } from "lucide-react";

const STYLES = {
  spread: { icon: BarChart3, color: "text-[#98c1d9]", label: "Spread" },
  total: { icon: Layers, color: "text-[#e0fbfc]", label: "Total" },
  moneyline: { icon: DollarSign, color: "text-[#ee6c4d]", label: "ML" },
};

export default function BetTypeBadge({ betType }) {
  const style = STYLES[betType] || { icon: BarChart3, color: "text-white", label: betType };
  const Icon = style.icon;
  return (
    <span className="flex items-center gap-1 bg-white/10 border border-white/10 text-white text-xs font-semibold px-2.5 py-1 rounded-full">
      <Icon size={12} className={style.color} />
      {style.label}
    </span>
  );
}