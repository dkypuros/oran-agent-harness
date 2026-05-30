import * as React from "react";
import { cn } from "@/lib/utils";

export type BadgeVariant = "default" | "success" | "warning" | "muted" | "danger";

const variantClass: Record<BadgeVariant, string> = {
  default: "bg-primary text-primary-foreground",
  success: "bg-green-100 text-green-800",
  warning: "bg-yellow-100 text-yellow-800",
  muted: "bg-muted text-muted-foreground",
  danger: "bg-red-100 text-red-800",
};

export function Badge({
  variant = "default",
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: BadgeVariant }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded px-2 py-0.5 text-xs font-medium",
        variantClass[variant],
        className,
      )}
      {...props}
    />
  );
}
