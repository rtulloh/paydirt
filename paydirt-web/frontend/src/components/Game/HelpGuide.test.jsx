import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import HelpGuide from './HelpGuide';

// Mock fetch
global.fetch = vi.fn();

describe('HelpGuide', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state initially', () => {
    // Mock a pending fetch
    global.fetch.mockImplementation(() => new Promise(() => {}));
    
    render(<HelpGuide onBackToMenu={() => {}} />);
    
    expect(screen.getByText('Loading guide...')).toBeInTheDocument();
  });

  it('displays guide content when loaded', async () => {
    const mockContent = '# Test Guide\n\nThis is test content.';
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ content: mockContent, title: 'Paydirt User Guide' }),
    });
    
    render(<HelpGuide onBackToMenu={() => {}} />);
    
    await waitFor(() => {
      expect(screen.getByText('Paydirt User Guide')).toBeInTheDocument();
    });
    
    // The markdown should be rendered
    expect(screen.getByText('Test Guide')).toBeInTheDocument();
    expect(screen.getByText('This is test content.')).toBeInTheDocument();
  });

  it('displays error state when fetch fails', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
    });
    
    render(<HelpGuide onBackToMenu={() => {}} />);
    
    await waitFor(() => {
      expect(screen.getByText('Error Loading Guide')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Failed to load guide')).toBeInTheDocument();
  });

  it('calls onBackToMenu when back button is clicked', async () => {
    const mockOnBackToMenu = vi.fn();
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ content: '# Guide', title: 'Paydirt User Guide' }),
    });
    
    render(<HelpGuide onBackToMenu={mockOnBackToMenu} />);
    
    await waitFor(() => {
      expect(screen.getByText('Paydirt User Guide')).toBeInTheDocument();
    });
    
    // Click the back button in the header
    const backButtons = screen.getAllByText('BACK TO MENU');
    await userEvent.click(backButtons[0]);
    
    expect(mockOnBackToMenu).toHaveBeenCalledTimes(1);
  });

  it('renders markdown content correctly', async () => {
    const mockContent = `# Main Title

## Section 1

Some text with **bold** and *italic*.

- List item 1
- List item 2

\`\`\`bash
echo "code block"
\`\`\`
`;
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ content: mockContent, title: 'Test Guide' }),
    });
    
    render(<HelpGuide onBackToMenu={() => {}} />);
    
    await waitFor(() => {
      expect(screen.getByText('Main Title')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Section 1')).toBeInTheDocument();
    expect(screen.getByText('List item 1')).toBeInTheDocument();
    expect(screen.getByText('List item 2')).toBeInTheDocument();
  });

  it('calls onBackToMenu when error state back button is clicked', async () => {
    const mockOnBackToMenu = vi.fn();
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    });
    
    render(<HelpGuide onBackToMenu={mockOnBackToMenu} />);
    
    await waitFor(() => {
      expect(screen.getByText('Error Loading Guide')).toBeInTheDocument();
    });
    
    await userEvent.click(screen.getByText('BACK TO MENU'));
    
    expect(mockOnBackToMenu).toHaveBeenCalledTimes(1);
  });
});
