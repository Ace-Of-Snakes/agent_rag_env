import { ButtonHTMLAttributes, forwardRef } from 'react';
import './Button.scss';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      children,
      disabled,
      className = '',
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        className={`btn btn--${variant} btn--${size} ${className}`}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && <span className="btn__spinner" />}
        {!isLoading && leftIcon && <span className="btn__icon">{leftIcon}</span>}
        {children && <span className="btn__text">{children}</span>}
        {!isLoading && rightIcon && <span className="btn__icon">{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = 'Button';
