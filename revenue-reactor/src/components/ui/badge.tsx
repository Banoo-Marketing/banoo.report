import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground',
        secondary: 'border-transparent bg-secondary text-secondary-foreground',
        outline: 'text-foreground',
        urgent: 'border-red-200 bg-red-100 text-red-800',
        likely: 'border-orange-200 bg-orange-100 text-orange-800',
        possible: 'border-yellow-200 bg-yellow-100 text-yellow-800',
        high: 'border-red-200 bg-red-100 text-red-800',
        watch: 'border-yellow-200 bg-yellow-100 text-yellow-800',
        safe: 'border-green-200 bg-green-100 text-green-800',
      },
    },
    defaultVariants: { variant: 'default' },
  }
)

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
