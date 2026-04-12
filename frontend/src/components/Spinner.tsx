interface Props {
  className?: string
}

export function CardSpinner({ className = 'h-32' }: Props) {
  return (
    <div className={`flex items-center justify-center ${className}`}>
      <div className="w-5 h-5 border-2 border-app-border border-t-accent rounded-full animate-spin" />
    </div>
  )
}
