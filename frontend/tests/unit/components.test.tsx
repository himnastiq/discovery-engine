import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { ErrorState } from '@/components/ui/ErrorState';
import { Tabs } from '@/components/ui/Tabs';
import { AppHeader } from '@/components/shell/AppHeader';

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('Design System Primitives (P8.6)', () => {
  it('renders Button with variants and handles click events', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click Me</Button>);
    const btn = screen.getByRole('button', { name: /click me/i });
    expect(btn).toBeInTheDocument();
    fireEvent.click(btn);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('renders Button in loading state and disables interaction', () => {
    render(<Button isLoading>Submit</Button>);
    const btn = screen.getByRole('button');
    expect(btn).toBeDisabled();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders Badge with domain-specific styling', () => {
    const { rerender } = render(<Badge variant="movie">Movies</Badge>);
    expect(screen.getByText('Movies')).toBeInTheDocument();

    rerender(<Badge variant="product">Products</Badge>);
    expect(screen.getByText('Products')).toBeInTheDocument();

    rerender(<Badge variant="article">Articles</Badge>);
    expect(screen.getByText('Articles')).toBeInTheDocument();
  });

  it('renders Card with header, title, and content slots', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Test Card</CardTitle>
        </CardHeader>
        <CardContent>Card Body</CardContent>
      </Card>
    );
    expect(screen.getByText('Test Card')).toBeInTheDocument();
    expect(screen.getByText('Card Body')).toBeInTheDocument();
  });

  it('renders ErrorState with retry callback', () => {
    const handleRetry = vi.fn();
    render(
      <ErrorState
        title="Failed to Load Recommendations"
        message="500 Internal Server Error"
        onRetry={handleRetry}
      />
    );
    expect(screen.getByText('Failed to Load Recommendations')).toBeInTheDocument();
    expect(screen.getByText('500 Internal Server Error')).toBeInTheDocument();

    const retryBtn = screen.getByRole('button', { name: /try again/i });
    fireEvent.click(retryBtn);
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });

  it('renders Tabs and handles tab selection', () => {
    const handleTabChange = vi.fn();
    const tabs = [
      { id: 'for-you', label: 'For You' },
      { id: 'compare', label: 'Compare' },
    ];
    render(<Tabs tabs={tabs} activeTab="for-you" onTabChange={handleTabChange} />);
    const compareTab = screen.getByRole('tab', { name: /compare/i });
    fireEvent.click(compareTab);
    expect(handleTabChange).toHaveBeenCalledWith('compare');
  });

  it('renders AppHeader with Ask AI button and invokes onOpenChat callback (P13.24)', () => {
    const handleOpenChat = vi.fn();
    renderWithClient(
      <AppHeader
        currentType="movies"
        onTypeChange={vi.fn()}
        currentUser="1"
        onUserChange={vi.fn()}
        onOpenChat={handleOpenChat}
      />
    );

    const askAiBtn = screen.getByRole('button', { name: /open discovery assistant/i });
    expect(askAiBtn).toBeInTheDocument();
    fireEvent.click(askAiBtn);
    expect(handleOpenChat).toHaveBeenCalledTimes(1);
  });
});

