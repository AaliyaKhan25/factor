export default function Card({
  children,
  className = "",
  hoverable = false,
  onClick,
}: {
  children: React.ReactNode;
  className?: string;
  hoverable?: boolean;
  onClick?: () => void;
}) {
  return (
    <section
      onClick={onClick}
      className={`rounded-2xl border border-line bg-white p-5 shadow-card transition-all duration-200 ${
        hoverable ? "cursor-pointer hover:-translate-y-0.5 hover:border-brand-dark/20 hover:shadow-hover" : ""
      } ${className}`}
    >
      {children}
    </section>
  );
}
