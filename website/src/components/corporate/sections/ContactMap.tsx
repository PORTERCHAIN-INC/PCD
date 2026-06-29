const OFFICE_QUERY = encodeURIComponent("100 King Street West, Toronto, ON M5X 1A9, Canada");

interface ContactMapProps {
  title: string;
}

export default function ContactMap({ title }: ContactMapProps) {
  return (
    <div className="rounded-2xl overflow-hidden border border-primary/[0.06] shadow-premium bg-gray-bg aspect-[16/10] min-h-[200px]">
      <iframe
        title={title}
        src={`https://maps.google.com/maps?q=${OFFICE_QUERY}&t=m&z=15&output=embed&iwloc=near`}
        className="w-full h-full border-0"
        loading="lazy"
        referrerPolicy="no-referrer-when-downgrade"
        allowFullScreen
      />
    </div>
  );
}
