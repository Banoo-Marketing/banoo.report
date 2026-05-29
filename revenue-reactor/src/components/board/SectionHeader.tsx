interface Props {
  emoji: string
  title: string
  count: number
  subtitle?: string
}

export function SectionHeader({ emoji, title, count, subtitle }: Props) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <span className="text-2xl">{emoji}</span>
      <div>
        <h2 className="text-lg font-bold text-gray-900">
          {title} <span className="text-gray-400 font-normal text-base">({count})</span>
        </h2>
        {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
      </div>
    </div>
  )
}
