// Purpose: Provides jest.config logic and exports for apps\web.
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.js'],
  moduleNameMapper: {
    '^@tripraft/ui/Toast$': '<rootDir>/../../packages/ui/src/Toast.jsx',
    '^@/(.*)$': '<rootDir>/src/$1',
    '\\.(css|svg)$': '<rootDir>/tests/styleMock.cjs',
  },
  transform: { '^.+\\.(js|jsx)$': 'babel-jest' },
  testMatch: ['**/__tests__/**/*.test.[jt]s?(x)'],
  moduleFileExtensions: ['js', 'jsx', 'json'],
  clearMocks: true,
};
