module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.js'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^firebase/firestore$': '<rootDir>/src/__mocks__/firebase/firestore.js',
    '^firebase/app$': '<rootDir>/src/__mocks__/firebase/app.js',
    '^../firebase/authService$': '<rootDir>/src/__mocks__/firebase/authService.js',
    '^../../firebase/authService$': '<rootDir>/src/__mocks__/firebase/authService.js',
  },
  transform: {
    '^.+\\.(js|jsx)$': 'babel-jest',
  },
  transformIgnorePatterns: [
    'node_modules/(?!(firebase|@firebase)/)',
  ],
  testMatch: ['**/__tests__/**/*.test.js'],
  moduleFileExtensions: ['js', 'jsx', 'json'],
  collectCoverageFrom: [
    'src/**/*.{js,jsx}',
    '!src/**/*.test.{js,jsx}',
    '!src/main.jsx',
  ],
};
