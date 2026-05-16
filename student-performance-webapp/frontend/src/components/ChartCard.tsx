import type { ReactNode } from "react";

// Wrapper for charts with title and consistent styling
interface ChartCardProps {
  title: string;
  children: ReactNode;
  className?: string; //CSS classes (tailwind) we're saying it MAY exist n if it did it's string 
  //when exists it's h-80 custim height (taller box) 
  // i had issues with the charts being out of the chartcard hihihi (sloppy)
}

export default function ChartCard({ title, children, className = "" }: ChartCardProps) {
  //children (the actual chart) sits below the <h3>
  return (
    <div className={`bg-white rounded-2xl shadow-lg p-6 ${className}`}>
      <h3 className="text-lg font-semibold text-gray-700 mb-4">{title}</h3>
      {children}
    </div>
  );
}