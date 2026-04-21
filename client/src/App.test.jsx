import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import App from './App';

// Mock fetch globally
global.fetch = vi.fn();

// Mock localStorage
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: (key) => store[key] || null,
    setItem: (key, value) => {
      store[key] = value.toString();
    },
    removeItem: (key) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    global.fetch.mockClear();
  });

  describe('Command Submission', () => {
    it('should submit a command when user is authenticated', async () => {
      const user = userEvent.setup();
      
      // Mock auth endpoints
      global.fetch.mockImplementation((url) => {
        if (url.includes('/health')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({ model: 'test-model' })),
          });
        }
        if (url.includes('/api/v1/command')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({
              result: { output: 'Command executed successfully' },
            })),
          });
        }
        return Promise.reject(new Error('Unknown endpoint'));
      });

      // Set up authenticated state
      localStorage.setItem('nexus_access_token', 'test-token');
      localStorage.setItem('nexus_user_email', 'test@example.com');
      localStorage.setItem('nexus_user_role', 'GENERAL');

      render(<App />);

      // Wait for component to load
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type a command/i)).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/Type a command/i);
      const sendButton = screen.getByRole('button', { name: /Send/i });

      // Type and submit command
      await user.type(input, 'check system status');
      await user.click(sendButton);

      // Verify command was sent
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/v1/command'),
          expect.objectContaining({
            method: 'POST',
            headers: expect.objectContaining({
              Authorization: 'Bearer test-token',
            }),
          })
        );
      });

      // Verify response appears in chat
      await waitFor(() => {
        expect(screen.getByText(/Command executed successfully/i)).toBeInTheDocument();
      });
    });

    it('should not submit command when user is not authenticated', async () => {
      const user = userEvent.setup();

      global.fetch.mockImplementation((url) => {
        if (url.includes('/health')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({ model: 'test-model' })),
          });
        }
        return Promise.reject(new Error('Unknown endpoint'));
      });

      render(<App />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Sign in to unlock/i)).toBeInTheDocument();
      });

      const sendButton = screen.getByRole('button', { name: /Send/i });
      expect(sendButton).toBeDisabled();
    });

    it('should clear input after successful submission', async () => {
      const user = userEvent.setup();

      global.fetch.mockImplementation((url) => {
        if (url.includes('/health')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({ model: 'test-model' })),
          });
        }
        if (url.includes('/api/v1/command')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({
              result: { output: 'Done' },
            })),
          });
        }
        return Promise.reject(new Error('Unknown endpoint'));
      });

      localStorage.setItem('nexus_access_token', 'test-token');
      localStorage.setItem('nexus_user_email', 'test@example.com');

      render(<App />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type a command/i)).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/Type a command/i);
      const sendButton = screen.getByRole('button', { name: /Send/i });

      await user.type(input, 'test command');
      await user.click(sendButton);

      await waitFor(() => {
        expect(input.value).toBe('');
      });
    });
  });

  describe('Confirmation Dialog', () => {
    it('should display confirmation dialog for write actions', async () => {
      const user = userEvent.setup();

      global.fetch.mockImplementation((url) => {
        if (url.includes('/health')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({ model: 'test-model' })),
          });
        }
        if (url.includes('/api/v1/command')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({
              result: {
                prompt_id: 'prompt-123',
                message: 'Are you sure you want to restart the service?',
              },
            })),
          });
        }
        return Promise.reject(new Error('Unknown endpoint'));
      });

      localStorage.setItem('nexus_access_token', 'test-token');
      localStorage.setItem('nexus_user_email', 'test@example.com');

      render(<App />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type a command/i)).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/Type a command/i);
      const sendButton = screen.getByRole('button', { name: /Send/i });

      await user.type(input, 'restart the service');
      await user.click(sendButton);

      // Verify confirmation message appears in chat
      await waitFor(() => {
        const messages = screen.getAllByText(/Are you sure you want to restart/i);
        expect(messages.length).toBeGreaterThan(0);
      }, { timeout: 3000 });

      // Verify confirmation buttons are present
      const confirmButtons = screen.getAllByRole('button', { name: /Confirm/i });
      expect(confirmButtons.length).toBeGreaterThan(0);
    });

    it('should execute action when confirmation is accepted', async () => {
      const user = userEvent.setup();

      global.fetch.mockImplementation((url) => {
        if (url.includes('/health')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({ model: 'test-model' })),
          });
        }
        if (url.includes('/api/v1/command')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({
              result: {
                prompt_id: 'prompt-123',
                message: 'Confirm restart?',
              },
            })),
          });
        }
        if (url.includes('/api/v1/confirm')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({
              result: { output: 'Service restarted successfully' },
            })),
          });
        }
        return Promise.reject(new Error('Unknown endpoint'));
      });

      localStorage.setItem('nexus_access_token', 'test-token');
      localStorage.setItem('nexus_user_email', 'test@example.com');

      render(<App />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type a command/i)).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/Type a command/i);
      const sendButton = screen.getByRole('button', { name: /Send/i });

      await user.type(input, 'restart service');
      await user.click(sendButton);

      // Wait for confirmation message
      await waitFor(() => {
        const messages = screen.getAllByText(/Confirm restart/i);
        expect(messages.length).toBeGreaterThan(0);
      }, { timeout: 3000 });

      // Find and click the confirm button in the confirmation dialog
      const confirmButtons = screen.getAllByRole('button', { name: /Confirm/i });
      const confirmButton = confirmButtons[confirmButtons.length - 1]; // Get the last one (in dialog)
      await user.click(confirmButton);

      // Verify execution result appears
      await waitFor(() => {
        expect(screen.getByText(/Service restarted successfully/i)).toBeInTheDocument();
      }, { timeout: 3000 });
    });

    it('should cancel action when confirmation is rejected', async () => {
      const user = userEvent.setup();

      global.fetch.mockImplementation((url) => {
        if (url.includes('/health')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({ model: 'test-model' })),
          });
        }
        if (url.includes('/api/v1/command')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({
              result: {
                prompt_id: 'prompt-123',
                message: 'Confirm action?',
              },
            })),
          });
        }
        if (url.includes('/api/v1/confirm')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({
              result: { output: 'Action cancelled' },
            })),
          });
        }
        return Promise.reject(new Error('Unknown endpoint'));
      });

      localStorage.setItem('nexus_access_token', 'test-token');
      localStorage.setItem('nexus_user_email', 'test@example.com');

      render(<App />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type a command/i)).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/Type a command/i);
      const sendButton = screen.getByRole('button', { name: /Send/i });

      await user.type(input, 'delete file');
      await user.click(sendButton);

      // Wait for confirmation message
      await waitFor(() => {
        const messages = screen.getAllByText(/Confirm action/i);
        expect(messages.length).toBeGreaterThan(0);
      }, { timeout: 3000 });

      // Find and click the cancel button
      const cancelButtons = screen.getAllByRole('button', { name: /Cancel/i });
      const cancelButton = cancelButtons[cancelButtons.length - 1]; // Get the last one (in dialog)
      await user.click(cancelButton);

      // Verify cancellation message appears
      await waitFor(() => {
        expect(screen.getByText(/Action cancelled/i)).toBeInTheDocument();
      }, { timeout: 3000 });
    });
  });

  describe('Error Display', () => {
    it('should display error message on network failure', async () => {
      const user = userEvent.setup();

      global.fetch.mockImplementation((url) => {
        if (url.includes('/health')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({ model: 'test-model' })),
          });
        }
        if (url.includes('/api/v1/command')) {
          return Promise.reject(new Error('Failed to fetch'));
        }
        return Promise.reject(new Error('Unknown endpoint'));
      });

      localStorage.setItem('nexus_access_token', 'test-token');
      localStorage.setItem('nexus_user_email', 'test@example.com');

      render(<App />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type a command/i)).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/Type a command/i);
      const sendButton = screen.getByRole('button', { name: /Send/i });

      await user.type(input, 'test command');
      await user.click(sendButton);

      // Verify error message appears
      await waitFor(() => {
        expect(screen.getByText(/backend service is currently unavailable/i)).toBeInTheDocument();
      });
    });

    it('should display error message on timeout', async () => {
      const user = userEvent.setup();

      global.fetch.mockImplementation((url) => {
        if (url.includes('/health')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({ model: 'test-model' })),
          });
        }
        if (url.includes('/api/v1/command')) {
          return Promise.reject(new Error('Request timed out'));
        }
        return Promise.reject(new Error('Unknown endpoint'));
      });

      localStorage.setItem('nexus_access_token', 'test-token');
      localStorage.setItem('nexus_user_email', 'test@example.com');

      render(<App />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type a command/i)).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/Type a command/i);
      const sendButton = screen.getByRole('button', { name: /Send/i });

      await user.type(input, 'test command');
      await user.click(sendButton);

      // Verify timeout error message appears
      await waitFor(() => {
        expect(screen.getByText(/timed out/i)).toBeInTheDocument();
      });
    });

    it('should display error message on unauthorized access', async () => {
      const user = userEvent.setup();

      global.fetch.mockImplementation((url) => {
        if (url.includes('/health')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({ model: 'test-model' })),
          });
        }
        if (url.includes('/api/v1/command')) {
          return Promise.resolve({
            ok: false,
            status: 401,
            text: () => Promise.resolve(JSON.stringify({
              detail: 'Unauthorized',
            })),
          });
        }
        return Promise.reject(new Error('Unknown endpoint'));
      });

      localStorage.setItem('nexus_access_token', 'test-token');
      localStorage.setItem('nexus_user_email', 'test@example.com');

      render(<App />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type a command/i)).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/Type a command/i);
      const sendButton = screen.getByRole('button', { name: /Send/i });

      await user.type(input, 'test command');
      await user.click(sendButton);

      // Verify unauthorized error message appears
      await waitFor(() => {
        expect(screen.getByText(/session has expired/i)).toBeInTheDocument();
      });
    });

    it('should display error message on forbidden access', async () => {
      const user = userEvent.setup();

      global.fetch.mockImplementation((url) => {
        if (url.includes('/health')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({ model: 'test-model' })),
          });
        }
        if (url.includes('/api/v1/command')) {
          return Promise.resolve({
            ok: false,
            status: 403,
            text: () => Promise.resolve(JSON.stringify({
              detail: 'Forbidden',
            })),
          });
        }
        return Promise.reject(new Error('Unknown endpoint'));
      });

      localStorage.setItem('nexus_access_token', 'test-token');
      localStorage.setItem('nexus_user_email', 'test@example.com');

      render(<App />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type a command/i)).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/Type a command/i);
      const sendButton = screen.getByRole('button', { name: /Send/i });

      await user.type(input, 'test command');
      await user.click(sendButton);

      // Verify forbidden error message appears
      await waitFor(() => {
        expect(screen.getByText(/don't have permission/i)).toBeInTheDocument();
      });
    });

    it('should display error message when system is busy', async () => {
      const user = userEvent.setup();

      global.fetch.mockImplementation((url) => {
        if (url.includes('/health')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({ model: 'test-model' })),
          });
        }
        if (url.includes('/api/v1/command')) {
          return Promise.resolve({
            ok: false,
            status: 503,
            text: () => Promise.resolve(JSON.stringify({
              detail: 'System busy',
            })),
          });
        }
        return Promise.reject(new Error('Unknown endpoint'));
      });

      localStorage.setItem('nexus_access_token', 'test-token');
      localStorage.setItem('nexus_user_email', 'test@example.com');

      render(<App />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type a command/i)).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/Type a command/i);
      const sendButton = screen.getByRole('button', { name: /Send/i });

      await user.type(input, 'test command');
      await user.click(sendButton);

      // Verify busy error message appears
      await waitFor(() => {
        expect(screen.getByText(/system is currently busy/i)).toBeInTheDocument();
      });
    });

    it('should mask sensitive data in responses', async () => {
      const user = userEvent.setup();

      global.fetch.mockImplementation((url) => {
        if (url.includes('/health')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({ model: 'test-model' })),
          });
        }
        if (url.includes('/api/v1/command')) {
          return Promise.resolve({
            ok: true,
            text: () => Promise.resolve(JSON.stringify({
              result: { output: 'API key: AIzaSyDummyKeyForTesting1234567890' },
            })),
          });
        }
        return Promise.reject(new Error('Unknown endpoint'));
      });

      localStorage.setItem('nexus_access_token', 'test-token');
      localStorage.setItem('nexus_user_email', 'test@example.com');

      render(<App />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type a command/i)).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/Type a command/i);
      const sendButton = screen.getByRole('button', { name: /Send/i });

      await user.type(input, 'get api key');
      await user.click(sendButton);

      // Verify sensitive data is masked
      await waitFor(() => {
        expect(screen.getByText(/\[masked-api-key\]/i)).toBeInTheDocument();
        expect(screen.queryByText(/AIzaSyDummyKeyForTesting/)).not.toBeInTheDocument();
      });
    });
  });
});
