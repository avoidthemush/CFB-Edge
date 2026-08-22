const BET_TYPES = ["all", "spread", "total", "moneyline"];
const BOOKS = ["all", "draftkings", "fanduel"];

function Segment({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`text-xs font-semibold px-3 py-1.5 rounded-full capitalize transition-colors ${
        active ? "bg-[#ee6c4d] text-white" : "text-white/60 hover:bg-white/10"
      }`}
    >
      {children}
    </button>
  );
}

export default function FilterBar({ betType, setBetType, book, setBook, sortOrder, setSortOrder }) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 mb-6 flex flex-wrap items-center gap-5">
      <div className="flex items-center gap-2">
        <span className="text-[10px] font-bold text-[#98c1d9] uppercase tracking-wider">Type</span>
        {BET_TYPES.map((bt) => (
          <Segment key={bt} active={betType === bt} onClick={() => setBetType(bt)}>
            {bt === "moneyline" ? "ML" : bt}
          </Segment>
        ))}
      </div>

      <div className="flex items-center gap-2">
        <span className="text-[10px] font-bold text-[#98c1d9] uppercase tracking-wider">Book</span>
        {BOOKS.map((b) => (
          <Segment key={b} active={book === b} onClick={() => setBook(b)}>
            {b === "draftkings" ? "DK" : b === "fanduel" ? "FD" : b}
          </Segment>
        ))}
      </div>

      <div className="flex items-center gap-2 ml-auto">
        <span className="text-[10px] font-bold text-[#98c1d9] uppercase tracking-wider">Sort</span>
        <select
          value={sortOrder}
          onChange={(e) => setSortOrder(e.target.value)}
          className="text-xs font-medium px-3 py-1.5 rounded-full bg-white/10 text-white border-none"
        >
          <option value="soonest" className="text-black">Kickoff: Soonest</option>
          <option value="latest" className="text-black">Kickoff: Latest</option>
        </select>
      </div>
    </div>
  );
}