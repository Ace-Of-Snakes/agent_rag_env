import './Spinner.scss';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function Spinner({ size = 'md', className = '' }: SpinnerProps) {
  return (
    <div className={`spinner spinner--${size} ${className}`}>
      <div className="spinner__circle" />
    </div>
  );
}
