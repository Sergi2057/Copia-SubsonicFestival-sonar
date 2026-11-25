// src/test/setup.js
// Se ejecuta antes de cada archivo de tests: añade expect(...).toBeInTheDocument() y similares
import '@testing-library/jest-dom/vitest';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
