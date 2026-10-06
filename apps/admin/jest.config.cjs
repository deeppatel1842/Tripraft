// Purpose: Provides jest.config logic and exports for apps\admin.
module.exports = { testEnvironment: 'jsdom', setupFilesAfterEnv: ['@testing-library/jest-dom'], transform: { '^.+\\.[jt]sx?$': 'babel-jest' }, testMatch: ['**/tests/**/*.test.jsx'], clearMocks: true };
