import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary/20 text-primary",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        destructive: "border-transparent bg-brand-red/20 text-brand-red",
        outline: "border-border text-foreground",
        success: "border-transparent bg-brand-green/20 text-brand-green",
        warning: "border-transparent bg-brand-orange/20 text-brand-orange",
        sarcasm: "border-brand-orange/30 bg-brand-orange/10 text-brand-orange",
        misinfo: "border-brand-red/30 bg-brand-red/10 text-brand-red",
        safe: "border-brand-green/30 bg-brand-green/10 text-brand-green",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
