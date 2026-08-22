import Image from "next/image";

const LOGOS = {
  draftkings: "/logos/draftkings.svg",
  fanduel: "/logos/fanduel.svg",
};

export default function BookBadge({ book }) {
  const src = LOGOS[book];
  if (!src) {
    return (
      <span className="bg-white/10 text-white text-xs font-bold px-2.5 py-1 rounded-full capitalize">
        {book}
      </span>
    );
  }
  return (
    <div className="flex items-center justify-center h-6">
      <Image
        src={src}
        alt={book}
        width={48}
        height={16}
        className="h-5 w-auto object-contain"
      />
    </div>
  );
}