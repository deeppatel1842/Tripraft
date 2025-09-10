# Project Directory Structure

## Root Directory Structure

```
travel-planner/
├── README.md
├── LICENSE
├── .gitignore
├── docs/
│   ├── API_DOCUMENTATION.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── DEVELOPMENT_SETUP.md
│   └── USER_STORIES.md
├── web-app/                        # React Web Application
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── public/
│   │   ├── index.html
│   │   ├── favicon.ico
│   │   └── manifest.json
│   └── src/
│       ├── components/             # Reusable UI Components
│       │   ├── common/
│       │   ├── forms/
│       │   ├── layout/
│       │   └── maps/
│       ├── pages/                  # Page Components
│       │   ├── auth/
│       │   ├── dashboard/
│       │   ├── trip-creation/
│       │   ├── trip-details/
│       │   ├── expenses/
│       │   └── profile/
│       ├── hooks/                  # Custom React Hooks
│       ├── store/                  # Redux Store Configuration
│       │   ├── slices/
│       │   ├── api/
│       │   └── middleware/
│       ├── services/               # API Services
│       ├── utils/                  # Utility Functions
│       ├── types/                  # TypeScript Type Definitions
│       ├── constants/              # App Constants
│       └── assets/                 # Static Assets
│           ├── images/
│           ├── icons/
│           └── styles/
├── backend/                        # Node.js Backend API
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── app.ts                 # Express App Configuration
│   │   ├── server.ts              # Server Entry Point
│   │   ├── controllers/           # Route Controllers
│   │   │   ├── auth.controller.ts
│   │   │   ├── trip.controller.ts
│   │   │   ├── itinerary.controller.ts
│   │   │   └── expense.controller.ts
│   │   ├── services/              # Business Logic Services
│   │   │   ├── itinerary.service.ts
│   │   │   ├── clustering.service.ts
│   │   │   ├── external-api.service.ts
│   │   │   └── notification.service.ts
│   │   ├── routes/                # API Routes
│   │   ├── middleware/            # Express Middleware
│   │   ├── models/                # Data Models
│   │   ├── utils/                 # Utility Functions
│   │   ├── config/                # Configuration Files
│   │   └── types/                 # TypeScript Definitions
│   ├── tests/                     # Test Files
│   └── dist/                      # Compiled JavaScript
├── mobile-app/                    # Future: React Native Mobile App
│   ├── README.md
│   └── PLANNING.md               # Mobile implementation planning
├── shared/                        # Shared Code Between Web & Backend
│   ├── types/                     # Shared TypeScript Types
│   ├── constants/                 # Shared Constants
│   └── utils/                     # Shared Utility Functions
├── cloud-functions/               # Firebase Cloud Functions
│   ├── package.json
│   ├── src/
│   │   ├── triggers/
│   │   ├── scheduled/
│   │   └── https/
│   └── lib/
├── database/                      # Database Related Files
│   ├── firestore-rules/
│   ├── security-rules/
│   ├── indexes/
│   └── seed-data/
├── infrastructure/                # Infrastructure as Code
│   ├── terraform/
│   ├── docker/
│   └── k8s/
├── scripts/                       # Build and Deployment Scripts
│   ├── setup.sh
│   ├── deploy.sh
│   └── test.sh
└── .github/                       # GitHub Actions CI/CD
    └── workflows/
        ├── web-ci.yml
        ├── backend-ci.yml
        └── deploy.yml
```

## Web App Detailed Structure

```
web-app/src/
├── components/
│   ├── common/
│   │   ├── Button/
│   │   │   ├── index.ts
│   │   │   ├── Button.tsx
│   │   │   ├── Button.styles.ts
│   │   │   └── Button.test.tsx
│   │   ├── Input/
│   │   ├── Modal/
│   │   ├── LoadingSpinner/
│   │   ├── Avatar/
│   │   └── Toast/
│   ├── forms/
│   │   ├── TripCreationForm/
│   │   ├── ExpenseForm/
│   │   ├── InviteForm/
│   │   └── AuthForm/
│   ├── layout/
│   │   ├── Header/
│   │   ├── Sidebar/
│   │   ├── Footer/
│   │   └── Layout/
│   └── maps/
│       ├── ItineraryMap/
│       ├── LocationPicker/
│       └── RouteDisplay/
├── pages/
│   ├── auth/
│   │   ├── LoginPage/
│   │   ├── RegisterPage/
│   │   └── ForgotPasswordPage/
│   ├── dashboard/
│   │   ├── DashboardPage/
│   │   ├── TripListPage/
│   │   └── ProfilePage/
│   ├── trip-creation/
│   │   ├── DestinationPage/
│   │   ├── DateSelectionPage/
│   │   ├── BudgetPage/
│   │   └── PlanSelectionPage/
│   ├── trip-details/
│   │   ├── TripOverviewPage/
│   │   ├── ItineraryPage/
│   │   ├── TransportPage/
│   │   └── GroupManagementPage/
│   └── expenses/
│       ├── ExpenseListPage/
│       ├── AddExpensePage/
│       └── BalancesPage/
├── hooks/
│   ├── useAuth.ts
│   ├── useTrips.ts
│   ├── useExpenses.ts
│   ├── useLocalStorage.ts
│   └── useDebounce.ts
├── store/
│   ├── index.ts
│   ├── slices/
│   │   ├── authSlice.ts
│   │   ├── tripSlice.ts
│   │   ├── expenseSlice.ts
│   │   └── uiSlice.ts
│   ├── api/
│   │   ├── authApi.ts
│   │   ├── tripApi.ts
│   │   └── baseApi.ts
│   └── middleware/
│       ├── errorHandler.ts
│       └── logger.ts
├── services/
│   ├── firebase/
│   │   ├── auth.service.ts
│   │   ├── firestore.service.ts
│   │   └── storage.service.ts
│   ├── api/
│   │   ├── http.client.ts
│   │   ├── trip.service.ts
│   │   └── expense.service.ts
│   └── maps/
│       └── leaflet.service.ts
├── utils/
│   ├── date.utils.ts
│   ├── currency.utils.ts
│   ├── validation.utils.ts
│   └── format.utils.ts
├── types/
│   ├── auth.types.ts
│   ├── trip.types.ts
│   ├── expense.types.ts
│   └── api.types.ts
├── constants/
│   ├── colors.ts
│   ├── breakpoints.ts
│   ├── api.constants.ts
│   └── app.constants.ts
└── assets/
    ├── images/
    │   ├── hero/
    │   ├── icons/
    │   └── placeholders/
    ├── styles/
    │   ├── globals.css
    │   └── tailwind.css
    └── fonts/
```

## Backend Detailed Structure

```
backend/src/
├── controllers/
│   ├── auth.controller.ts
│   ├── trip.controller.ts
│   ├── itinerary.controller.ts
│   ├── expense.controller.ts
│   └── user.controller.ts
├── services/
│   ├── itinerary/
│   │   ├── generation.service.ts
│   │   ├── clustering.service.ts
│   │   └── optimization.service.ts
│   ├── external-api/
│   │   ├── amadeus.service.ts
│   │   ├── booking.service.ts
│   │   ├── google-maps.service.ts
│   │   └── tripadvisor.service.ts
│   ├── firebase/
│   │   ├── firestore.service.ts
│   │   ├── auth.service.ts
│   │   └── storage.service.ts
│   ├── notification/
│   │   └── push.service.ts
│   └── expense/
│       ├── calculation.service.ts
│       └── split.service.ts
├── routes/
│   ├── index.ts
│   ├── auth.routes.ts
│   ├── trip.routes.ts
│   ├── itinerary.routes.ts
│   └── expense.routes.ts
├── middleware/
│   ├── auth.middleware.ts
│   ├── validation.middleware.ts
│   ├── error.middleware.ts
│   └── rate-limit.middleware.ts
├── models/
│   ├── User.model.ts
│   ├── Trip.model.ts
│   ├── Expense.model.ts
│   └── Itinerary.model.ts
├── utils/
│   ├── encryption.utils.ts
│   ├── date.utils.ts
│   ├── email.utils.ts
│   └── algorithm.utils.ts
├── config/
│   ├── database.config.ts
│   ├── api.config.ts
│   ├── firebase.config.ts
│   └── environment.config.ts
└── types/
    ├── api.types.ts
    ├── database.types.ts
    └── external.types.ts
```

## Key Naming Conventions

### File Naming
- **Components**: PascalCase directories with index.ts export
- **Screens**: PascalCase with "Screen" suffix
- **Services**: camelCase with ".service.ts" suffix
- **Utils**: camelCase with ".utils.ts" suffix
- **Types**: camelCase with ".types.ts" suffix
- **Constants**: camelCase with ".constants.ts" suffix

### Code Conventions
- **Variables**: camelCase
- **Constants**: UPPER_SNAKE_CASE
- **Functions**: camelCase
- **Classes**: PascalCase
- **Interfaces**: PascalCase with "I" prefix for complex types
- **Types**: PascalCase with "T" prefix for union types
- **Enums**: PascalCase

### Git Branch Strategy
- **main**: Production-ready code
- **develop**: Integration branch
- **feature/**: Feature branches (feature/trip-creation)
- **bugfix/**: Bug fix branches (bugfix/expense-calculation)
- **hotfix/**: Critical production fixes (hotfix/auth-security)
- **release/**: Release preparation (release/v1.0.0)

### Environment Configuration
- **development**: Local development
- **staging**: Pre-production testing
- **production**: Live production environment

This structure ensures scalability, maintainability, and clear separation of concerns for your large-scale travel planner application.
