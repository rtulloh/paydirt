import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import PuntOptionsPanel from './PuntOptionsPanel';

describe('PuntOptionsPanel', () => {
  const defaultProps = {
    ballPosition: 25,
    onSelect: vi.fn(),
    onCancel: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders normal punt option by default', () => {
    render(<PuntOptionsPanel {...defaultProps} />);
    
    expect(screen.getByText('PUNT OPTIONS')).toBeInTheDocument();
    expect(screen.getByText('NORMAL PUNT')).toBeInTheDocument();
    expect(screen.getByText('CANCEL')).toBeInTheDocument();
  });

  it('shows coffin corner option when not inside 5 yard line', () => {
    render(<PuntOptionsPanel {...defaultProps} ballPosition={25} />);
    
    expect(screen.getByText('COFFIN-CORNER PUNT')).toBeInTheDocument();
  });

  it('shows short-drop option when inside 5 yard line', () => {
    render(<PuntOptionsPanel {...defaultProps} ballPosition={96} />);
    
    expect(screen.getByText('SHORT-DROP PUNT')).toBeInTheDocument();
    expect(screen.getByText(/Defenders will get Free All-Out Kick Rush/)).toBeInTheDocument();
  });

  it('shows mandatory short-drop message when at 5 yard line or closer', () => {
    render(<PuntOptionsPanel {...defaultProps} ballPosition={97} />);
    
    expect(screen.getByText(/Short-Drop Punt is mandatory/)).toBeInTheDocument();
  });

  it('calls onSelect with normal punt options when normal punt is clicked', () => {
    render(<PuntOptionsPanel {...defaultProps} />);
    
    fireEvent.click(screen.getByText('NORMAL PUNT'));
    
    expect(defaultProps.onSelect).toHaveBeenCalledWith({
      short_drop: false,
      coffin_corner_yards: 0,
    });
  });

  it('shows coffin corner input when coffin corner is selected', () => {
    render(<PuntOptionsPanel {...defaultProps} ballPosition={30} />);
    
    fireEvent.click(screen.getByText('COFFIN-CORNER PUNT'));
    
    expect(screen.getByText('Yards to subtract (0-25):')).toBeInTheDocument();
    expect(screen.getByText('CONFIRM')).toBeInTheDocument();
    expect(screen.getByText('BACK')).toBeInTheDocument();
  });

  it('calls onSelect with coffin corner yards when confirmed', () => {
    render(<PuntOptionsPanel {...defaultProps} ballPosition={30} />);
    
    fireEvent.click(screen.getByText('COFFIN-CORNER PUNT'));
    
    const input = screen.getByRole('spinbutton');
    fireEvent.change(input, { target: { value: '15' } });
    
    fireEvent.click(screen.getByText('CONFIRM'));
    
    expect(defaultProps.onSelect).toHaveBeenCalledWith({
      short_drop: false,
      coffin_corner_yards: 15,
    });
  });

  it('shows automatic OOB message when 15+ yards subtracted', () => {
    render(<PuntOptionsPanel {...defaultProps} ballPosition={30} />);
    
    fireEvent.click(screen.getByText('COFFIN-CORNER PUNT'));
    
    const input = screen.getByRole('spinbutton');
    fireEvent.change(input, { target: { value: '18' } });
    
    expect(screen.getByText(/Automatic out of bounds/)).toBeInTheDocument();
  });

  it('calls onCancel when cancel is clicked', () => {
    render(<PuntOptionsPanel {...defaultProps} />);
    
    fireEvent.click(screen.getByText('CANCEL'));
    
    expect(defaultProps.onCancel).toHaveBeenCalled();
  });

  it('goes back from coffin corner input when back is clicked', () => {
    render(<PuntOptionsPanel {...defaultProps} ballPosition={30} />);
    
    fireEvent.click(screen.getByText('COFFIN-CORNER PUNT'));
    expect(screen.getByText('COFFIN-CORNER PUNT')).toBeInTheDocument();
    
    fireEvent.click(screen.getByText('BACK'));
    
    expect(screen.getByText('COFFIN-CORNER PUNT')).toBeInTheDocument();
  });
});
