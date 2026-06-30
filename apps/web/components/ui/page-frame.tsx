import { ReactNode } from "react";

type PageFrameProps = {
  title: string;
  description: string;
  children?: ReactNode;
};

export function PageFrame({ title, description, children }: PageFrameProps) {
  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        <p className="text-sm text-foreground/70 mt-1">{description}</p>
      </header>
      {children}
    </section>
  );
}
