# Published file guide

Every published source/configuration file is listed below. Legal source formats have purpose comments; strict JSON, generated contracts/lockfiles and binary assets are described here without invalid edits.

| File | What it does |
|---|---|
| `.gitattributes` | Keeps shell/workflow line endings portable and treats SQLite catalogs as binary data. |
| `.github/instructions/intro.instructions.md` | Documents intro.instructions for .github\instructions. |
| `.github/workflows/ci.yml` | GitHub discovery copy of infra/github/workflows/ci.yml; update the canonical file and run pnpm workflows:sync. |
| `.github/workflows/deploy.yml` | GitHub discovery copy of infra/github/workflows/deploy.yml; update the canonical file and run pnpm workflows:sync. |
| `.gitignore` | Excludes local settings, secrets, data, dependencies, build output, and archived extras from publication. |
| `README.md` | Project overview and the shortest setup/start/verification instructions. |
| `apps/admin/.env.example` | Documents public configuration keys and placeholder values; copy locally and keep real credentials out of Git. |
| `apps/admin/babel.config.cjs` | Provides babel.config logic and exports for apps\admin. |
| `apps/admin/eslint.config.mjs` | Applies the shared syntax/error lint rules to apps\admin. |
| `apps/admin/index.html` | Defines the HTML document/root element loaded by the React frontend. |
| `apps/admin/jest.config.cjs` | Provides jest.config logic and exports for apps\admin. |
| `apps/admin/package.json` | Declares dependencies, exports and development commands for the apps\admin workspace package. |
| `apps/admin/src/App.tsx` | Renders the admin console with initialized server-account authorization, readiness and ingestion audit results. |
| `apps/admin/src/env.d.ts` | Renders the admin console with initialized server-account authorization, readiness and ingestion audit results. |
| `apps/admin/src/main.tsx` | Renders the admin console with initialized server-account authorization, readiness and ingestion audit results. |
| `apps/admin/src/styles.css` | Styles the styles interface, including its layout and interaction states. |
| `apps/admin/tests/access.test.jsx` | Regression tests for access, including success and failure behavior. |
| `apps/admin/tests/viteEnvTransform.cjs` | Test fixture/configuration helper for vite Env Transform. |
| `apps/admin/tsconfig.json` | Selects TypeScript compiler options and checked source for apps\admin. |
| `apps/admin/vite.config.ts` | Configures the React build and local API proxy for apps\admin. |
| `apps/web/.env.example` | Documents public configuration keys and placeholder values; copy locally and keep real credentials out of Git. |
| `apps/web/babel.config.cjs` | Provides babel.config logic and exports for apps\web. |
| `apps/web/eslint.config.js` | Applies the shared syntax/error lint rules to apps\web. |
| `apps/web/index.html` | Defines the HTML document/root element loaded by the React frontend. |
| `apps/web/jest.config.cjs` | Provides jest.config logic and exports for apps\web. |
| `apps/web/package.json` | Declares dependencies, exports and development commands for the apps\web workspace package. |
| `apps/web/public/favicon.svg` | Visual asset used by apps\web\public: favicon. |
| `apps/web/public/images/ANIMATION_IMAGES.md` | Documents ANIMATION IMAGES for apps\web\public\images. |
| `apps/web/public/images/README.md` | Documents README for apps\web\public\images. |
| `apps/web/public/images/confuse_man.png` | Visual asset used by apps\web\public\images: confuse man. |
| `apps/web/public/images/happy.png` | Visual asset used by apps\web\public\images: happy. |
| `apps/web/public/images/man.png` | Visual asset used by apps\web\public\images: man. |
| `apps/web/public/images/map.png` | Visual asset used by apps\web\public\images: map. |
| `apps/web/public/images/passport.png` | Visual asset used by apps\web\public\images: passport. |
| `apps/web/public/images/plane.png` | Visual asset used by apps\web\public\images: plane. |
| `apps/web/public/images/search.png` | Visual asset used by apps\web\public\images: search. |
| `apps/web/public/images/travel_man.png` | Visual asset used by apps\web\public\images: travel man. |
| `apps/web/public/images/trip_plan.png` | Visual asset used by apps\web\public\images: trip plan. |
| `apps/web/src/App.jsx` | Renders the App interface within apps\web\src. |
| `apps/web/src/__tests__/apiClient.test.js` | Regression tests for api Client, including success and failure behavior. |
| `apps/web/src/__tests__/authService.test.js` | Regression tests for auth Service, including success and failure behavior. |
| `apps/web/src/__tests__/cacheAndFreshness.test.jsx` | Regression tests for cache And Freshness, including success and failure behavior. |
| `apps/web/src/__tests__/chatPanelState.test.jsx` | Regression tests for chat Panel State, including success and failure behavior. |
| `apps/web/src/__tests__/chatQuery.test.jsx` | Regression tests for chat Query, including success and failure behavior. |
| `apps/web/src/__tests__/chatSocket.test.jsx` | Regression tests for chat Socket, including success and failure behavior. |
| `apps/web/src/__tests__/consentAndSettlement.test.jsx` | Regression tests for consent And Settlement, including success and failure behavior. |
| `apps/web/src/__tests__/money.test.js` | Regression tests for money, including success and failure behavior. |
| `apps/web/src/__tests__/ownerAndInactivity.test.jsx` | Regression tests for owner And Inactivity, including success and failure behavior. |
| `apps/web/src/__tests__/p3Behavior.test.jsx` | Regression tests for p3 Behavior, including success and failure behavior. |
| `apps/web/src/__tests__/routes.test.jsx` | Regression tests for routes, including success and failure behavior. |
| `apps/web/src/__tests__/searchCancellation.test.jsx` | Regression tests for search Cancellation, including success and failure behavior. |
| `apps/web/src/__tests__/serviceContracts.test.js` | Regression tests for service Contracts, including success and failure behavior. |
| `apps/web/src/assets/placeholder-place.svg` | Visual asset used by apps\web\src\assets: placeholder place. |
| `apps/web/src/components/common/css/AnimatedBackground.css` | Styles the Animated Background interface, including its layout and interaction states. |
| `apps/web/src/components/common/css/DestinationAutocomplete.css` | Styles the Destination Autocomplete interface, including its layout and interaction states. |
| `apps/web/src/components/common/css/ErrorBoundary.css` | Styles the Error Boundary interface, including its layout and interaction states. |
| `apps/web/src/components/common/css/FeatureErrorBoundary.css` | Contains feature rendering failures and provides an actionable recovery screen. |
| `apps/web/src/components/common/css/Skeleton.css` | Styles the Skeleton interface, including its layout and interaction states. |
| `apps/web/src/components/common/css/UserAvatar.css` | Styles the User Avatar interface, including its layout and interaction states. |
| `apps/web/src/components/common/index.js` | Provides index logic and exports for apps\web\src\components\common. |
| `apps/web/src/components/common/jsx/AnimatedBackground.jsx` | Renders the Animated Background interface within apps\web\src\components\common\jsx. |
| `apps/web/src/components/common/jsx/DestinationAutocomplete.jsx` | Renders the Destination Autocomplete interface within apps\web\src\components\common\jsx. |
| `apps/web/src/components/common/jsx/ErrorBoundary.jsx` | Renders the Error Boundary interface within apps\web\src\components\common\jsx. |
| `apps/web/src/components/common/jsx/FeatureErrorBoundary.jsx` | Contains feature rendering failures and provides an actionable recovery screen. |
| `apps/web/src/components/common/jsx/GroupCardSkeleton.jsx` | Renders the Group Card Skeleton interface within apps\web\src\components\common\jsx. |
| `apps/web/src/components/common/jsx/PageSkeleton.jsx` | Renders the Page Skeleton interface within apps\web\src\components\common\jsx. |
| `apps/web/src/components/common/jsx/PlaceCardSkeleton.jsx` | Renders the Place Card Skeleton interface within apps\web\src\components\common\jsx. |
| `apps/web/src/components/common/jsx/UserAvatar.jsx` | Renders the User Avatar interface within apps\web\src\components\common\jsx. |
| `apps/web/src/components/layout/css/Footer.css` | Styles the Footer interface, including its layout and interaction states. |
| `apps/web/src/components/layout/css/Header.css` | Styles the Header interface, including its layout and interaction states. |
| `apps/web/src/components/layout/index.js` | Provides index logic and exports for apps\web\src\components\layout. |
| `apps/web/src/components/layout/jsx/Footer.jsx` | Renders the Footer interface within apps\web\src\components\layout\jsx. |
| `apps/web/src/components/layout/jsx/Header.jsx` | Renders the Header interface within apps\web\src\components\layout\jsx. |
| `apps/web/src/config/globalConfig.js` | Provides global Config logic and exports for apps\web\src\config. |
| `apps/web/src/context/AuthContext.jsx` | Provides authenticated account state, initialization, profile updates, and logout cache cleanup. |
| `apps/web/src/env.d.ts` | Provides env.d logic and exports for apps\web\src. |
| `apps/web/src/features/auth/css/Login.css` | Styles the Login interface, including its layout and interaction states. |
| `apps/web/src/features/auth/css/Signup.css` | Styles the Signup interface, including its layout and interaction states. |
| `apps/web/src/features/auth/index.js` | Provides index logic and exports for apps\web\src\features\auth. |
| `apps/web/src/features/auth/jsx/AuthPage.jsx` | Renders the Auth Page interface within apps\web\src\features\auth\jsx. |
| `apps/web/src/features/auth/jsx/InactivityTracker.jsx` | Warns about inactivity and resets the logout timer when activity resumes. |
| `apps/web/src/features/auth/jsx/Login.jsx` | Renders the Login interface within apps\web\src\features\auth\jsx. |
| `apps/web/src/features/auth/jsx/ProtectedRoute.jsx` | Renders the Protected Route interface within apps\web\src\features\auth\jsx. |
| `apps/web/src/features/auth/jsx/Signup.jsx` | Renders the Signup interface within apps\web\src\features\auth\jsx. |
| `apps/web/src/features/discover/css/GroupedPlaceGrid.css` | Styles the Grouped Place Grid interface, including its layout and interaction states. |
| `apps/web/src/features/discover/css/PlaceCard.css` | Styles the Place Card interface, including its layout and interaction states. |
| `apps/web/src/features/discover/css/PlaceDetailModal.css` | Styles the Place Detail Modal interface, including its layout and interaction states. |
| `apps/web/src/features/discover/css/PlaceGrid.css` | Styles the Place Grid interface, including its layout and interaction states. |
| `apps/web/src/features/discover/css/PlaceSearchPage.css` | Coordinates real place search, statistics and loading/error/empty states. |
| `apps/web/src/features/discover/css/SearchBar.css` | Fetches autocomplete suggestions and ignores cancelled or stale responses. |
| `apps/web/src/features/discover/css/SearchSuggestions.css` | Styles the Search Suggestions interface, including its layout and interaction states. |
| `apps/web/src/features/discover/index.js` | Provides index logic and exports for apps\web\src\features\discover. |
| `apps/web/src/features/discover/jsx/GroupedPlaceGrid.jsx` | Renders the Grouped Place Grid interface within apps\web\src\features\discover\jsx. |
| `apps/web/src/features/discover/jsx/PlaceCard.jsx` | Renders the Place Card interface within apps\web\src\features\discover\jsx. |
| `apps/web/src/features/discover/jsx/PlaceDetailModal.jsx` | Renders the Place Detail Modal interface within apps\web\src\features\discover\jsx. |
| `apps/web/src/features/discover/jsx/PlaceGrid.jsx` | Renders the Place Grid interface within apps\web\src\features\discover\jsx. |
| `apps/web/src/features/discover/jsx/PlaceSearchPage.jsx` | Coordinates real place search, statistics and loading/error/empty states. |
| `apps/web/src/features/discover/jsx/SearchBar.jsx` | Fetches autocomplete suggestions and ignores cancelled or stale responses. |
| `apps/web/src/features/discover/jsx/SearchSuggestions.jsx` | Renders the Search Suggestions interface within apps\web\src\features\discover\jsx. |
| `apps/web/src/features/expenses/css/ExpenseAnalytics.css` | Styles the Expense Analytics interface, including its layout and interaction states. |
| `apps/web/src/features/expenses/css/ExpenseHistoryModal.css` | Styles the Expense History Modal interface, including its layout and interaction states. |
| `apps/web/src/features/expenses/css/ExpenseManager.css` | Coordinates personal/group expense screens, editing, history and financial query updates. |
| `apps/web/src/features/expenses/css/SettlementHistoryModal.css` | Styles the Settlement History Modal interface, including its layout and interaction states. |
| `apps/web/src/features/expenses/css/SettlementModal.css` | Collects debt-bounded settlement payments and displays currency-aware history and save errors. |
| `apps/web/src/features/expenses/index.js` | Provides index logic and exports for apps\web\src\features\expenses. |
| `apps/web/src/features/expenses/jsx/ExpenseAnalytics.jsx` | Renders the Expense Analytics interface within apps\web\src\features\expenses\jsx. |
| `apps/web/src/features/expenses/jsx/ExpenseHistoryModal.jsx` | Renders the Expense History Modal interface within apps\web\src\features\expenses\jsx. |
| `apps/web/src/features/expenses/jsx/ExpenseManager.jsx` | Coordinates personal/group expense screens, editing, history and financial query updates. |
| `apps/web/src/features/expenses/jsx/ExpenseSummary.jsx` | Renders the Expense Summary interface within apps\web\src\features\expenses\jsx. |
| `apps/web/src/features/expenses/jsx/GroupBalances.jsx` | Renders the Group Balances interface within apps\web\src\features\expenses\jsx. |
| `apps/web/src/features/expenses/jsx/GroupManager.jsx` | Displays and manages expense groups, members, ownership controls and invitations. |
| `apps/web/src/features/expenses/jsx/GroupSummaryCards.jsx` | Renders the Group Summary Cards interface within apps\web\src\features\expenses\jsx. |
| `apps/web/src/features/expenses/jsx/MemberSpending.jsx` | Renders the Member Spending interface within apps\web\src\features\expenses\jsx. |
| `apps/web/src/features/expenses/jsx/ModeToggle.jsx` | Renders the Mode Toggle interface within apps\web\src\features\expenses\jsx. |
| `apps/web/src/features/expenses/jsx/PendingInvitations.jsx` | Renders the Pending Invitations interface within apps\web\src\features\expenses\jsx. |
| `apps/web/src/features/expenses/jsx/PersonalTabbedView.jsx` | Renders the Personal Tabbed View interface within apps\web\src\features\expenses\jsx. |
| `apps/web/src/features/expenses/jsx/SettlementHistoryModal.jsx` | Renders the Settlement History Modal interface within apps\web\src\features\expenses\jsx. |
| `apps/web/src/features/expenses/jsx/SettlementModal.jsx` | Collects debt-bounded settlement payments and displays currency-aware history and save errors. |
| `apps/web/src/features/expenses/jsx/TabbedGroupView.jsx` | Renders the Tabbed Group View interface within apps\web\src\features\expenses\jsx. |
| `apps/web/src/features/expenses/jsx/TransactionList.jsx` | Renders the Transaction List interface within apps\web\src\features\expenses\jsx. |
| `apps/web/src/features/expenses/jsx/TransactionModal.jsx` | Renders the Transaction Modal interface within apps\web\src\features\expenses\jsx. |
| `apps/web/src/features/itinerary/css/TripPlanner.css` | Styles the Trip Planner interface, including its layout and interaction states. |
| `apps/web/src/features/itinerary/index.js` | Provides index logic and exports for apps\web\src\features\itinerary. |
| `apps/web/src/features/itinerary/jsx/Checklist.jsx` | Renders the Checklist interface within apps\web\src\features\itinerary\jsx. |
| `apps/web/src/features/itinerary/jsx/Icon.jsx` | Renders the Icon interface within apps\web\src\features\itinerary\jsx. |
| `apps/web/src/features/itinerary/jsx/Itinerary.jsx` | Renders the Itinerary interface within apps\web\src\features\itinerary\jsx. |
| `apps/web/src/features/itinerary/jsx/ItineraryStop.jsx` | Renders the Itinerary Stop interface within apps\web\src\features\itinerary\jsx. |
| `apps/web/src/features/itinerary/jsx/SuggestedPlaces.jsx` | Renders the Suggested Places interface within apps\web\src\features\itinerary\jsx. |
| `apps/web/src/features/itinerary/jsx/TripForm.jsx` | Renders the Trip Form interface within apps\web\src\features\itinerary\jsx. |
| `apps/web/src/features/itinerary/jsx/TripMap.jsx` | Renders itinerary map markers and safe DOM-based popups. |
| `apps/web/src/features/itinerary/jsx/TripPlanCard.jsx` | Renders the Trip Plan Card interface within apps\web\src\features\itinerary\jsx. |
| `apps/web/src/features/itinerary/jsx/TripTips.jsx` | Renders the Trip Tips interface within apps\web\src\features\itinerary\jsx. |
| `apps/web/src/features/polls/PollFeed.jsx` | Renders poll choices, vote counts and voter panels using state and handlers supplied by chat. |
| `apps/web/src/features/scout/CrewCards.jsx` | Renders Crew question, confirmation, place and success cards. |
| `apps/web/src/features/scout/ScoutConsentCard.jsx` | Displays Scout consent choices and retries the original request after consent. |
| `apps/web/src/features/scout/aiBots.js` | Defines the shared Scout and Crew bot identities used by chat and member views. |
| `apps/web/src/features/trips/constants/mapConfig.js` | Provides map Config logic and exports for apps\web\src\features\trips\constants. |
| `apps/web/src/features/trips/constants/tabConfig.js` | Provides tab Config logic and exports for apps\web\src\features\trips\constants. |
| `apps/web/src/features/trips/css/CreateGroupModal.css` | Styles the Create Group Modal interface, including its layout and interaction states. |
| `apps/web/src/features/trips/css/GroupPlannerPage.css` | Styles the Group Planner Page interface, including its layout and interaction states. |
| `apps/web/src/features/trips/hooks/useMapRenderer.js` | Provides reusable React state/query behavior for Map Renderer. |
| `apps/web/src/features/trips/index.js` | Provides index logic and exports for apps\web\src\features\trips. |
| `apps/web/src/features/trips/jsx/CreateGroupModal.jsx` | Renders the Create Group Modal interface within apps\web\src\features\trips\jsx. |
| `apps/web/src/features/trips/jsx/GroupPlannerManager.jsx` | Renders the Group Planner Manager interface within apps\web\src\features\trips\jsx. |
| `apps/web/src/features/trips/jsx/GroupPlannerPage.jsx` | Renders the Group Planner Page interface within apps\web\src\features\trips\jsx. |
| `apps/web/src/features/trips/jsx/InvitationAcceptPage.jsx` | Renders the Invitation Accept Page interface within apps\web\src\features\trips\jsx. |
| `apps/web/src/features/trips/jsx/chat/ChatPanel.jsx` | Coordinates message rendering, live chat, AI cards, polls, optimistic sends and group-switch state. |
| `apps/web/src/features/trips/jsx/map/MapPanel.jsx` | Renders the Map Panel interface within apps\web\src\features\trips\jsx\map. |
| `apps/web/src/features/trips/jsx/shared/GroupSelector.jsx` | Renders the Group Selector interface within apps\web\src\features\trips\jsx\shared. |
| `apps/web/src/features/trips/jsx/tabs/CircleTab.jsx` | Renders the Circle Tab interface within apps\web\src\features\trips\jsx\tabs. |
| `apps/web/src/features/trips/jsx/tabs/ItineraryTab.jsx` | Renders the Itinerary Tab interface within apps\web\src\features\trips\jsx\tabs. |
| `apps/web/src/features/trips/jsx/tabs/LibraryTab.jsx` | Renders the Library Tab interface within apps\web\src\features\trips\jsx\tabs. |
| `apps/web/src/features/trips/jsx/tabs/LogisticsTab.jsx` | Renders the Logistics Tab interface within apps\web\src\features\trips\jsx\tabs. |
| `apps/web/src/features/trips/jsx/tabs/PulseTab.jsx` | Renders the Pulse Tab interface within apps\web\src\features\trips\jsx\tabs. |
| `apps/web/src/features/trips/jsx/tabs/TreasuryTab.jsx` | Renders the Treasury Tab interface within apps\web\src\features\trips\jsx\tabs. |
| `apps/web/src/features/trips/utils/formatters.js` | Provides formatters logic and exports for apps\web\src\features\trips\utils. |
| `apps/web/src/features/trips/utils/groupPlannerUtils.js` | Provides group Planner Utils logic and exports for apps\web\src\features\trips\utils. |
| `apps/web/src/hooks/useAiConsentQuery.js` | Provides reusable React state/query behavior for Ai Consent Query. |
| `apps/web/src/hooks/useChatQuery.js` | Manages paginated chat queries and optimistic sends while preserving concurrent messages. |
| `apps/web/src/hooks/useChatSocket.js` | Connects cookie-authenticated live chat and reports socket authentication/connection failures. |
| `apps/web/src/hooks/useExpenseQuery.js` | Coordinates React Query reads and mutations for expense groups, balances, expenses and settlements. |
| `apps/web/src/hooks/useGroupPlannerQuery.js` | Provides reusable React state/query behavior for Group Planner Query. |
| `apps/web/src/hooks/useGroupSocket.js` | Subscribes to cookie-authenticated trip workspace activity updates. |
| `apps/web/src/hooks/useNotesAutoSave.js` | Provides reusable React state/query behavior for Notes Auto Save. |
| `apps/web/src/hooks/usePlaceSearchQuery.js` | Provides reusable React state/query behavior for Place Search Query. |
| `apps/web/src/hooks/useTripPlannerQuery.js` | Provides reusable React state/query behavior for Trip Planner Query. |
| `apps/web/src/lib/chatCache.js` | Deduplicates message IDs across cached pages and reconciles optimistic send results. |
| `apps/web/src/lib/indexedDBPersister.js` | Stores and removes permitted query snapshots in IndexedDB. |
| `apps/web/src/lib/queryClientPersist.js` | Configures query caching while excluding financial/private queries and mutation state from persistence. |
| `apps/web/src/main.tsx` | Mounts the React application into the HTML root element. |
| `apps/web/src/pages/About.jsx` | Renders the About interface within apps\web\src\pages. |
| `apps/web/src/pages/Analytics.jsx` | Renders the Analytics interface within apps\web\src\pages. |
| `apps/web/src/pages/Contact.jsx` | Renders the Contact interface within apps\web\src\pages. |
| `apps/web/src/pages/ExpenseAnalytics.jsx` | Renders the Expense Analytics interface within apps\web\src\pages. |
| `apps/web/src/pages/ExpensePage.jsx` | Renders the Expense Page interface within apps\web\src\pages. |
| `apps/web/src/pages/HomePage.jsx` | Renders the Home Page interface within apps\web\src\pages. |
| `apps/web/src/pages/InvitationAccept.jsx` | Renders the Invitation Accept interface within apps\web\src\pages. |
| `apps/web/src/pages/Pricing.jsx` | Renders the Pricing interface within apps\web\src\pages. |
| `apps/web/src/pages/SmartInvitationHandler.jsx` | Renders the Smart Invitation Handler interface within apps\web\src\pages. |
| `apps/web/src/pages/TripPlanner.jsx` | Renders the Trip Planner interface within apps\web\src\pages. |
| `apps/web/src/pages/index.js` | Provides index logic and exports for apps\web\src\pages. |
| `apps/web/src/pages/styles/About.css` | Styles the About interface, including its layout and interaction states. |
| `apps/web/src/pages/styles/Analytics.css` | Styles the Analytics interface, including its layout and interaction states. |
| `apps/web/src/pages/styles/Contact.css` | Styles the Contact interface, including its layout and interaction states. |
| `apps/web/src/pages/styles/ExpenseAnalytics.css` | Styles the Expense Analytics interface, including its layout and interaction states. |
| `apps/web/src/pages/styles/ExpensePage.css` | Styles the Expense Page interface, including its layout and interaction states. |
| `apps/web/src/pages/styles/HomePage.css` | Styles the Home Page interface, including its layout and interaction states. |
| `apps/web/src/pages/styles/Pricing.css` | Styles the Pricing interface, including its layout and interaction states. |
| `apps/web/src/services/aiConsentApi.js` | Provides ai Consent Api logic and exports for apps\web\src\services. |
| `apps/web/src/services/chatApi.js` | Provides chat Api logic and exports for apps\web\src\services. |
| `apps/web/src/services/expenseApi.js` | Provides expense Api logic and exports for apps\web\src\services. |
| `apps/web/src/services/groupPlannerApi.js` | Provides group Planner Api logic and exports for apps\web\src\services. |
| `apps/web/src/services/pdfExportService.js` | Provides pdf Export Service logic and exports for apps\web\src\services. |
| `apps/web/src/services/placeSearchService.js` | Provides place Search Service logic and exports for apps\web\src\services. |
| `apps/web/src/services/sqlAuthService.js` | Handles cookie-based signup/login/refresh/profile/logout requests and session failure behavior. |
| `apps/web/src/services/tripPlannerService.js` | Provides trip Planner Service logic and exports for apps\web\src\services. |
| `apps/web/src/setupTests.js` | Provides setup Tests logic and exports for apps\web\src. |
| `apps/web/src/styles.css` | Styles the styles interface, including its layout and interaction states. |
| `apps/web/src/styles/global.css` | Styles the global interface, including its layout and interaction states. |
| `apps/web/src/utils/apiClient.js` | Sends web API requests with cookie credentials, CSRF headers, response handling and cancellation. |
| `apps/web/src/utils/apiLogger.js` | Provides api Logger logic and exports for apps\web\src\utils. |
| `apps/web/src/utils/coordinates.js` | Provides coordinates logic and exports for apps\web\src\utils. |
| `apps/web/src/utils/errorHandler.js` | Provides error Handler logic and exports for apps\web\src\utils. |
| `apps/web/src/utils/money.js` | Normalizes currency amounts, whole-cent splits and UUID payer changes. |
| `apps/web/src/utils/placeRating.js` | Provides place Rating logic and exports for apps\web\src\utils. |
| `apps/web/src/utils/timezoneUtils.js` | Provides timezone Utils logic and exports for apps\web\src\utils. |
| `apps/web/tests/styleMock.cjs` | Test fixture/configuration helper for style Mock. |
| `apps/web/tests/viteEnvTransform.cjs` | Test fixture/configuration helper for vite Env Transform. |
| `apps/web/tsconfig.json` | Selects TypeScript compiler options and checked source for apps\web. |
| `apps/web/vite.config.js` | Configures the React build and local API proxy for apps\web. |
| `data/catalog/travel_data_complete.db` | Reference place/location catalog used for travel search; preserve the binary dataset without source comments. |
| `data/seeds/README.md` | Documents README for data\seeds. |
| `docs/api.md` | Explains API envelopes, cookie authentication, generated client use and remaining schema coverage. |
| `docs/architecture.md` | Explains app/service/package boundaries, data ownership, auth and deployment architecture. |
| `docs/files.md` | Explains every published file, including strict JSON, generated artifacts and binary assets that cannot contain comments. |
| `docs/runbook.md` | Documents operation, verification, backups, and deployment prerequisites. |
| `docs/startup.md` | Documents the single-file launcher, one-time setup, runtime modes, ports, data and troubleshooting. |
| `infra/docker/.env.example` | Documents public configuration keys and placeholder values; copy locally and keep real credentials out of Git. |
| `infra/docker/docker-compose.yml` | Runs local PostgreSQL, Redis, API, and optional worker with persistent database/catalog/upload volumes. |
| `infra/github/workflows/ci.yml` | Canonical CI: install locked dependencies, check source, run tests/builds, and verify generated API declarations. |
| `infra/github/workflows/deploy.yml` | Canonical release workflow: verify source, then call the configured staging or production deployment hook. |
| `infra/terraform/README.md` | Documents README for infra\terraform. |
| `infra/tests/test_launcher.py` | Regression tests for launcher, including success and failure behavior. |
| `infra/tools/check_python.py` | Validates backend Python files against the Python 3.11 grammar used by CI and Docker. |
| `infra/tools/check_structure.py` | Checks required workspace files, discovered workflows, and Python/JavaScript/TypeScript import targets. |
| `infra/tools/dev-env.ps1` | Creates the optional isolated development environment without replacing archived local environments. |
| `infra/tools/document_files.py` | Adds valid file-purpose headers and regenerates this complete source/configuration file guide. |
| `infra/tools/export_openapi.py` | Exports registered Flask paths and explicit admin schemas using a migrated disposable database. |
| `infra/tools/sync-workflows.mjs` | Copies canonical workflows into the .github/workflows paths GitHub discovers. |
| `infra/tools/validate_infra.py` | Checks Compose paths, volumes and dependencies plus workflow YAML without claiming live deployment. |
| `package.json` | Defines workspace commands, pinned package-manager version, and shared development dependencies. |
| `packages/api-client/eslint.config.js` | Applies the shared syntax/error lint rules to packages\api-client. |
| `packages/api-client/package.json` | Declares dependencies, exports and development commands for the packages\api-client workspace package. |
| `packages/api-client/src/generated/schema.d.ts` | Generated API route/response contracts; regenerate through the documented OpenAPI tools rather than editing by hand. |
| `packages/api-client/src/index.ts` | Creates the generated-schema API client with cookie credentials and mutation CSRF headers, without automatic retries. |
| `packages/api-client/tsconfig.json` | Selects TypeScript compiler options and checked source for packages\api-client. |
| `packages/config/eslint.config.js` | Applies the shared syntax/error lint rules to packages\config. |
| `packages/config/package.json` | Declares dependencies, exports and development commands for the packages\config workspace package. |
| `packages/config/prettier.json` | Configures prettier for packages\config. |
| `packages/config/tsconfig.json` | Selects TypeScript compiler options and checked source for packages\config. |
| `packages/types/eslint.config.js` | Applies the shared syntax/error lint rules to packages\types. |
| `packages/types/package.json` | Declares dependencies, exports and development commands for the packages\types workspace package. |
| `packages/types/src/index.ts` | Exports shared UUID, money, account, API envelope and service-health TypeScript contracts. |
| `packages/types/tsconfig.json` | Selects TypeScript compiler options and checked source for packages\types. |
| `packages/ui/eslint.config.js` | Applies the shared syntax/error lint rules to packages\ui. |
| `packages/ui/package.json` | Declares dependencies, exports and development commands for the packages\ui workspace package. |
| `packages/ui/src/Toast.jsx` | Renders shared timed notifications used by application features. |
| `packages/ui/src/styles/Toast.css` | Renders shared timed notifications used by application features. |
| `pnpm-lock.yaml` | Locks resolved workspace dependencies for reproducible installation; generated by pnpm. |
| `pnpm-workspace.yaml` | Declares application, API, and shared-package workspace membership and permitted dependency build scripts. |
| `prettier.config.cjs` | Loads the shared formatting preset for repository configuration and new source files. |
| `services/api/.dockerignore` | Configures dockerignore for services\api. |
| `services/api/.env.example` | Documents public configuration keys and placeholder values; copy locally and keep real credentials out of Git. |
| `services/api/Dockerfile` | Builds the non-root Python API image and its production entry point. |
| `services/api/alembic.ini` | Configures alembic for services\api. |
| `services/api/app/__init__.py` | TripRaft Backend Application Enterprise-grade Flask backend. |
| `services/api/app/auth/__init__.py` | Users Domain Package Contains User and UserSession models and repositories. |
| `services/api/app/auth/models.py` | User Domain Models User, UserSession, and AuditLog models for authentication, session management,. |
| `services/api/app/auth/repository.py` | User Repository Data access layer for User entities. |
| `services/api/app/auth/routes/__init__.py` | Declares the services\api\app\auth\routes Python package and its public exports. |
| `services/api/app/auth/routes/auth.py` | Authentication Routes API endpoints for user authentication. |
| `services/api/app/auth/routes/users.py` | Users API Endpoints REST API for user authentication and profile management. |
| `services/api/app/auth/security/__init__.py` | Auth Infrastructure Package jwt.py         — JWT token creation/verification. |
| `services/api/app/auth/security/decorators.py` | Unified Authentication Decorators Single source of truth for route-protection across the entire backend. |
| `services/api/app/auth/security/jwt.py` | JWT Token Handler Creates and validates JWT tokens for authentication. |
| `services/api/app/auth/security/password.py` | Password Hashing Utilities Uses bcrypt for secure password hashing. |
| `services/api/app/auth/services/__init__.py` | Declares the services\api\app\auth\services Python package and its public exports. |
| `services/api/app/auth/services/auth_service.py` | Authentication Service Handles user registration, login, logout, and token management. |
| `services/api/app/auth/services/user_service.py` | User Service Business logic for user profile management. |
| `services/api/app/core/__init__.py` | Core utilities -- config, logging, exceptions, rate limiting, security. |
| `services/api/app/core/apiutils/__init__.py` | Utility modules. |
| `services/api/app/core/apiutils/database.py` | API Database Utilities Thin wrapper around the shared TravelDatabase from infrastructure. |
| `services/api/app/core/apiutils/responses.py` | Standardized API response utilities. Provides consistent response formatting across all endpoints. |
| `services/api/app/core/apiutils/validators.py` | Input validation utilities Provides validation and sanitization for API inputs. |
| `services/api/app/core/cache/__init__.py` | Cache Infrastructure Package Provides Redis-based caching with graceful fallback. |
| `services/api/app/core/cache/redis.py` | Redis Cache Client — Singleton with graceful fallback. Provides get/set/delete/exists with JSON serialization and. |
| `services/api/app/core/config.py` | Application Configuration Single source of truth for all backend settings. |
| `services/api/app/core/db/__init__.py` | Database Infrastructure Package connection.py  — SQLAlchemy engine for tripraft.db (users, expenses, groups). |
| `services/api/app/core/db/base.py` | Shared Declarative Base Every ORM model in the application MUST import Base from here. |
| `services/api/app/core/db/connection.py` | SQLAlchemy Connection Manager SINGLE SOURCE OF TRUTH for the ORM database connection. |
| `services/api/app/core/db/migration_checks.py` | Read-only checks that reject unsupported legacy identifier storage. |
| `services/api/app/core/db/travel_db.py` | Travel Data Database — travel_data_complete.db Connection manager for the travel reference database. |
| `services/api/app/core/db/uuid7.py` | UUIDv7 Generator (RFC 9562) Time-ordered, globally unique, cryptographically random identifiers. |
| `services/api/app/core/exceptions.py` | Custom Exception Hierarchy Framework-agnostic exception classes for the entire backend. |
| `services/api/app/core/external/__init__.py` | Third-party API clients. |
| `services/api/app/core/factory.py` | TripRaft Application Factory Creates and configures the Flask application with all routes and middleware. |
| `services/api/app/core/health.py` | Health Check Endpoint Liveness and readiness probes for Kubernetes / load balancers. |
| `services/api/app/core/idempotency.py` | Idempotency middleware. Stores the result of a mutating request keyed by its `Idempotency-Key`. |
| `services/api/app/core/json_utils.py` | JSON-boundary helpers for values emitted by ORM-backed services. |
| `services/api/app/core/logging.py` | Logging Configuration Extracted from the monolithic app.py for clean separation. |
| `services/api/app/core/middleware.py` | API Middleware Request ID injection, structured request/response logging. |
| `services/api/app/core/rate_limiter.py` | Rate Limiter Configuration Centralized rate limiting using Flask-Limiter with tiered limits and response headers. |
| `services/api/app/core/resilience.py` | Circuit breakers for external service calls. Wraps Ticketmaster, Nominatim, and SMTP with pybreaker to prevent. |
| `services/api/app/core/route_viewer.py` | API Route Viewer Provides a styled HTML / JSON endpoint listing all registered API routes. |
| `services/api/app/core/sanitize.py` | Input sanitization for user-provided text content. Strips HTML/script tags to prevent stored XSS. |
| `services/api/app/core/schemas/__init__.py` | Request/response validation schemas. |
| `services/api/app/core/schemas/auth.py` | Auth-related validation schemas. |
| `services/api/app/core/schemas/common.py` | Input Validation Schemas — backward-compatibility re-exports. All schemas have been split into per-domain modules.  This file re-exports. |
| `services/api/app/core/schemas/expense_groups.py` | Expense-group validation schemas. |
| `services/api/app/core/schemas/expenses.py` | Expense-related validation schemas. |
| `services/api/app/core/schemas/fields.py` | Shared marshmallow field types. Every identifier in this codebase is a UUIDv7 string (see. |
| `services/api/app/core/schemas/gp_chat.py` | Group-planner chat validation schemas. |
| `services/api/app/core/schemas/gp_checklist.py` | Group-planner checklist validation schemas. |
| `services/api/app/core/schemas/gp_places.py` | Group-planner place validation schemas. |
| `services/api/app/core/schemas/gp_polls.py` | Group-planner poll validation schemas. |
| `services/api/app/core/schemas/group_planner.py` | Group-planner group-level validation schemas. |
| `services/api/app/core/schemas/invitations.py` | Invitation validation schemas. |
| `services/api/app/core/schemas/places.py` | Place Ingestion Schemas (Pydantic v2) Single source of truth for all data validation in the ingestion pipeline. |
| `services/api/app/core/schemas/settlements.py` | Settlement validation schemas. |
| `services/api/app/core/schemas/trips.py` | Trip-planner validation schemas. |
| `services/api/app/core/schemas/users.py` | User Schemas Pydantic models for request/response validation. |
| `services/api/app/core/security.py` | Security Utilities CORS configuration, security headers, CSRF protection, and related utilities. |
| `services/api/app/core/workers/__init__.py` | Background jobs and scheduled tasks. |
| `services/api/app/core/workers/celery_app.py` | Celery Application Factory Configures the Celery worker with Redis as broker and result backend. |
| `services/api/app/core/workers/schedules.py` | Celery Beat Schedule Periodic tasks for maintenance, cache warming, and analytics. |
| `services/api/app/core/workers/tasks/__init__.py` | Task modules for Celery workers. |
| `services/api/app/core/workers/tasks/ai_tasks.py` | AI Background Tasks — Celery tasks for Scout agent processing. Tasks:. |
| `services/api/app/core/workers/tasks/analytics_tasks.py` | Analytics Tasks Cache warming and daily metrics aggregation. |
| `services/api/app/core/workers/tasks/chat_tasks.py` | Chat Background Tasks Scheduled maintenance for group chat messages. |
| `services/api/app/core/workers/tasks/cleanup_tasks.py` | Cleanup Tasks Scheduled maintenance: session expiry, soft-delete archival. |
| `services/api/app/core/workers/tasks/crew_tasks.py` | Crew Background Tasks — Celery tasks for @crew agent processing. Tasks:. |
| `services/api/app/core/workers/tasks/email_tasks.py` | Email Tasks Async email delivery via Celery.  Retries with exponential backoff. |
| `services/api/app/core/workers/tasks/notification_tasks.py` | Notification Tasks Async push / in-app notifications via Celery. |
| `services/api/app/expenses/__init__.py` | Expense domain models and business entities. |
| `services/api/app/expenses/models.py` | SQLAlchemy ORM Models for Expense Engine Base, User, and UserSession are imported from shared_db (single source of truth). |
| `services/api/app/expenses/routes/__init__.py` | Declares the services\api\app\expenses\routes Python package and its public exports. |
| `services/api/app/expenses/routes/expense_groups.py` | SQL-based Group Routes API endpoints for group operations using local SQL database. |
| `services/api/app/expenses/routes/expense_invitations.py` | SQL-based Invitation Routes API endpoints for managing group invitations. |
| `services/api/app/expenses/routes/expenses.py` | SQL-based Expense Routes API endpoints for expense operations using local SQL database. |
| `services/api/app/expenses/routes/settlements.py` | SQL-based Settlement Routes API endpoints for settlement operations using local SQL database. |
| `services/api/app/expenses/services/__init__.py` | Declares the services\api\app\expenses\services Python package and its public exports. |
| `services/api/app/expenses/services/expense_group_service.py` | SQL-based Group Service Handles group operations using local SQL database. |
| `services/api/app/expenses/services/expense_invite_service.py` | SQL-based Invitation Service Handles group invitations using local SQL database. |
| `services/api/app/expenses/services/expense_service.py` | SQL-based Expense Service Handles expense operations using local SQL database. |
| `services/api/app/expenses/services/money_lock.py` | Serialize money validation and mutation in the same transaction. |
| `services/api/app/expenses/services/settlement_service.py` | SQL-based Settlement Service Handles settling debts between users. |
| `services/api/app/itinerary/__init__.py` | Declares the services\api\app\itinerary Python package and its public exports. |
| `services/api/app/itinerary/routes/__init__.py` | Declares the services\api\app\itinerary\routes Python package and its public exports. |
| `services/api/app/itinerary/routes/gp_checklist.py` | Checklist Routes for Group Planner Flask API routes for checklist operations. |
| `services/api/app/itinerary/routes/gp_events.py` | Events Routes for Group Planner Flask API routes for Ticketmaster events integration. |
| `services/api/app/itinerary/routes/gp_export.py` | Export & Integration Routes for Group Planner GET  /groups/<id>/export/pdf   — download trip PDF. |
| `services/api/app/itinerary/routes/gp_places.py` | Place Routes for Group Planner Flask API routes for place operations. |
| `services/api/app/itinerary/routes/trips.py` | Trip Planner API Routes REST API endpoints for generating trip itineraries. |
| `services/api/app/itinerary/services/__init__.py` | Declares the services\api\app\itinerary\services Python package and its public exports. |
| `services/api/app/itinerary/services/checklist_service.py` | Checklist Service for Group Planner Handles all checklist operations using local SQL database. |
| `services/api/app/itinerary/services/events_service.py` | Events Service for Group Planner Fetches events from Ticketmaster API for travel destinations. |
| `services/api/app/itinerary/services/export_service.py` | Export service for Group Planner. Generates PDF itinerary and iCal calendar files. |
| `services/api/app/itinerary/services/travel_place_service.py` | Place Service for Group Planner Handles all place/destination operations using unified SQL database (pateldeep.db). |
| `services/api/app/notifications/__init__.py` | Declares the services\api\app\notifications Python package and its public exports. |
| `services/api/app/notifications/email/__init__.py` | Email Infrastructure Package Provides SMTP-based email sending for notifications. |
| `services/api/app/notifications/email/config.py` | Email Configuration Module Controls which email notifications are enabled/disabled. |
| `services/api/app/notifications/email/smtp.py` | Email Service — SMTP-based email sending. Provides methods for sending various notification emails. |
| `services/api/app/notifications/routes/__init__.py` | Declares the services\api\app\notifications\routes Python package and its public exports. |
| `services/api/app/notifications/routes/gp_notifications.py` | Notification Routes for Group Planner GET  /notifications            — list user's notifications (paginated). |
| `services/api/app/notifications/services/__init__.py` | Declares the services\api\app\notifications\services Python package and its public exports. |
| `services/api/app/notifications/services/email_service.py` | Email Service Professional email handling for expense engine. |
| `services/api/app/notifications/services/notification_service.py` | Notification Service for Group Planner Handles creating, querying, and managing in-app notifications. |
| `services/api/app/places/__init__.py` | Place and location domain models for geographic data. |
| `services/api/app/places/location_models.py` | Data models for places API Provides query methods for places, cities, states, and countries. |
| `services/api/app/places/location_repository.py` | Location Database Utilities Thin wrapper around the shared DatabaseConnection pool from repository.py. |
| `services/api/app/places/models.py` | Place Search Models Data models for place search results. |
| `services/api/app/places/repository.py` | Place Search Database Module Thread-safe database connection pool for the travel database. |
| `services/api/app/places/routes/__init__.py` | Declares the services\api\app\places\routes Python package and its public exports. |
| `services/api/app/places/routes/admin_places.py` | Admin Places API CRUD and bulk ingestion endpoints for travel data management. |
| `services/api/app/places/routes/gp_destinations.py` | Group Planner SQL-Only Routes Pure SQL backend - NO FIREBASE. |
| `services/api/app/places/routes/locations.py` | Locations API routes (Unified) — DEPRECATED Consolidated endpoints for countries, states, cities, and places. |
| `services/api/app/places/routes/places.py` | Place Search API Routes Flask blueprint for place search endpoints. |
| `services/api/app/places/search/__init__.py` | Declares the services\api\app\places\search Python package and its public exports. |
| `services/api/app/places/search/web_search.py` | Web Search Client — DuckDuckGo (DDGS) with SearXNG fallback. Provides a unified web search interface for Scout agent queries when. |
| `services/api/app/places/services/__init__.py` | Declares the services\api\app\places\services Python package and its public exports. |
| `services/api/app/places/services/data_ingestion_service.py` | Data Ingestion Service Validates, inserts, updates and bulk-imports travel entities. |
| `services/api/app/places/services/destination_service.py` | Destination Service (formerly PlacesService) Fetches destination/places data from the travel database. |
| `services/api/app/places/services/place_search_service.py` | Place Search Service Business logic for place search operations. |
| `services/api/app/scout/__init__.py` | Declares the services\api\app\scout Python package and its public exports. |
| `services/api/app/scout/llm/__init__.py` | Declares the services\api\app\scout\llm Python package and its public exports. |
| `services/api/app/scout/llm/ollama_client.py` | Ollama HTTP Client — with circuit breaker, timeouts, and graceful fallback. Talks to the Ollama REST API running on an internal Docker network. |
| `services/api/app/scout/llm/output_validator.py` | LLM Output Validator — Sanitizes and validates all LLM-generated text before it is stored or shown to users. |
| `services/api/app/scout/llm/prompt_templates.py` | Prompt Templates — Hardcoded server-side, never user-modifiable. Each template is a function that accepts structured context and returns. |
| `services/api/app/scout/models.py` | SQLAlchemy ORM Models for AI Agent System Tables for consent management, preference profiles, and agent logging. |
| `services/api/app/scout/routes/__init__.py` | Declares the services\api\app\scout\routes Python package and its public exports. |
| `services/api/app/scout/routes/ai_confirm.py` | AI Crew Confirm Routes — REST API for confirming @crew destructive actions. Endpoints:. |
| `services/api/app/scout/routes/ai_consent.py` | AI Consent Routes — REST API for managing Scout agent consent. Endpoints:. |
| `services/api/app/scout/services/__init__.py` | Declares the services\api\app\scout\services Python package and its public exports. |
| `services/api/app/scout/services/consent_gate.py` | Consent Gate — Enforces AI data access consent before any processing. Checks per-user, per-group consent records in ai_consent table. |
| `services/api/app/scout/services/crew_agent_service.py` | Crew Agent Service — Core orchestrator for @crew CRUD operations in group chat. Responsibilities:. |
| `services/api/app/scout/services/crew_conversation.py` | Crew Conversation State Manager — Redis-backed multi-turn Q&A state. Each user in a group gets an isolated conversation slot with TTL. |
| `services/api/app/scout/services/crew_parsers.py` | Crew Intent Classifier & Entity Extractor — Tiered parsing for @crew commands. Tier 1: Pure regex for unambiguous, fully-specified commands (confidence=1.0). |
| `services/api/app/scout/services/scout_agent_service.py` | Scout Agent Service — Core logic for the @scout travel guide agent. Responsibilities:. |
| `services/api/app/trips/__init__.py` | Group planner domain models for collaborative travel planning. |
| `services/api/app/trips/models.py` | SQLAlchemy ORM Models for Group Planner All database tables for collaborative travel planning. |
| `services/api/app/trips/realtime/__init__.py` | Declares the services\api\app\trips\realtime Python package and its public exports. |
| `services/api/app/trips/realtime/events.py` | Socket.IO event handlers for Group Planner real-time collaboration. Rooms: one room per group, named "group:<group_id>". |
| `services/api/app/trips/realtime/socketio_ext.py` | Flask-SocketIO extension singleton. Import `socketio` from here anywhere in the backend to emit events. |
| `services/api/app/trips/routes/__init__.py` | Declares the services\api\app\trips\routes Python package and its public exports. |
| `services/api/app/trips/routes/gp_chat.py` | Chat Routes for Group Planner REST API endpoints for group messaging. |
| `services/api/app/trips/routes/gp_groups.py` | Group Routes for Group Planner Flask API routes for group operations. |
| `services/api/app/trips/routes/gp_invitations.py` | Invitation Routes for Group Planner Flask API routes for invitation operations. |
| `services/api/app/trips/routes/gp_polls.py` | Poll Routes for Group Planner Flask API routes for poll operations. |
| `services/api/app/trips/routes/gp_vault.py` | Vault Routes for Group Planner File upload / download / list / delete for the logistics vault. |
| `services/api/app/trips/services/__init__.py` | Declares the services\api\app\trips\services Python package and its public exports. |
| `services/api/app/trips/services/chat_service.py` | Chat Service — Core group messaging logic. Handles message CRUD, read receipts, unread counts. |
| `services/api/app/trips/services/poll_service.py` | Poll Service for Group Planner Handles all poll/voting operations using local SQL database. |
| `services/api/app/trips/services/travel_group_service.py` | Group Service for Group Planner Handles all group operations using unified SQL database (pateldeep.db). |
| `services/api/app/trips/services/trip_invite_service.py` | Invitation Service for Group Planner Handles group invitations using unified SQL database (tripraft.db). |
| `services/api/app/trips/services/vault_service.py` | Vault Service for Group Planner Handles file upload/download for the logistics vault. |
| `services/api/docker-entrypoint.sh` | Copies the seed catalog only when needed, applies API migrations and starts the supplied server/worker command. |
| `services/api/gunicorn.conf.py` | Gunicorn Configuration Production server settings with graceful shutdown and worker recycling. |
| `services/api/migrations/README` | Configures README for services\api\migrations. |
| `services/api/migrations/env.py` | Alembic Environment Configuration Connects Alembic to the app's SQLAlchemy metadata and database URL. |
| `services/api/migrations/script.py.mako` | Configures script.py for services\api\migrations. |
| `services/api/migrations/versions/119b418945ce_json_to_jsonb_postgresql.py` | json_to_jsonb_postgresql PostgreSQL-only migration: converts JSON columns to JSONB for indexing,. |
| `services/api/migrations/versions/60621bfec6f2_add_missing_composite_indexes.py` | add_missing_composite_indexes Revision ID: 60621bfec6f2. |
| `services/api/migrations/versions/74866d910457_uuidv7_primary_keys.py` | Retire the unsafe integer-to-UUID schema rewrite. Revision ID: 74866d910457. |
| `services/api/migrations/versions/75118e6ab634_initial_schema.py` | Frozen UUID-native application schema (2026-10-02). Revision ID: 75118e6ab634. |
| `services/api/migrations/versions/83f1d84d08e4_add_ai_consent_preferences_agent_logs.py` | add_ai_consent_preferences_agent_logs Revision ID: 83f1d84d08e4. |
| `services/api/migrations/versions/a0a12823fc65_materialized_views_postgresql.py` | materialized_views_postgresql PostgreSQL-only migration: creates two materialized views for. |
| `services/api/migrations/versions/a5b6c7d8e9f0_add_checklist_metadata_and_chat_fks.py` | Persist checklist metadata and protect chat message references. Revision ID: a5b6c7d8e9f0. |
| `services/api/migrations/versions/b7c8d9e0f1a2_complete_vault_and_place_time_schema.py` | Complete vault/time coverage and validate UUID-native existing databases. Revision ID: b7c8d9e0f1a2. |
| `services/api/migrations/versions/c4d5e6f7a8b9_add_chat_tables.py` | add_chat_tables Revision ID: c4d5e6f7a8b9. |
| `services/api/migrations/versions/d4a1c3e8f9b0_add_settlement_and_verification_audit_columns.py` | Persist settlement deletion and email-verification audit timestamps. Revision ID: d4a1c3e8f9b0. |
| `services/api/migrations/versions/e336ee48cb0f_add_date_partitioning_postgresql.py` | add_date_partitioning_postgresql PostgreSQL-only migration: converts expenses, expense_history, and. |
| `services/api/migrations/versions/e80825488cb5_add_audit_log_table.py` | add_audit_log_table Revision ID: e80825488cb5. |
| `services/api/migrations/versions/f2a3b4c5d6e7_add_chat_message_archival.py` | Add reversible archival support for group chat messages. Revision ID: f2a3b4c5d6e7. |
| `services/api/openapi.json` | Generated API route/response contracts; regenerate through the documented OpenAPI tools rather than editing by hand. |
| `services/api/package.json` | Declares dependencies, exports and development commands for the services\api workspace package. |
| `services/api/pytest.ini` | Configures pytest for services\api. |
| `services/api/requirements-dev.txt` | Pins the test, critical-error lint and infrastructure validation tools excluded from the production image. |
| `services/api/requirements.txt` | Pins the Flask API runtime dependencies, database drivers, authentication, workers and export integrations. |
| `services/api/ruff.toml` | Configures ruff for services\api. |
| `services/api/run.py` | TripRaft Backend -- Main Entry Point Run this file to start the Flask server. |
| `services/api/tests/conftest.py` | Test fixture/configuration helper for conftest. |
| `services/api/tests/test_ai_consent.py` | Regression tests for ai consent, including success and failure behavior. |
| `services/api/tests/test_auth_tokens.py` | Regression tests for auth tokens, including success and failure behavior. |
| `services/api/tests/test_crew_expense_deletion.py` | Regression tests for crew expense deletion, including success and failure behavior. |
| `services/api/tests/test_csrf.py` | Regression tests for csrf, including success and failure behavior. |
| `services/api/tests/test_endpoint_inventory.py` | Regression tests for endpoint inventory, including success and failure behavior. |
| `services/api/tests/test_group_access_controls.py` | Regression tests for group access controls, including success and failure behavior. |
| `services/api/tests/test_group_planner_smoke.py` | Regression tests for group planner smoke, including success and failure behavior. |
| `services/api/tests/test_idempotency.py` | Regression tests for idempotency, including success and failure behavior. |
| `services/api/tests/test_migration_contract.py` | Regression tests for migration contract, including success and failure behavior. |
| `services/api/tests/test_money_concurrency.py` | Regression tests for money concurrency, including success and failure behavior. |
| `services/api/tests/test_money_integrity.py` | Regression tests for money integrity, including success and failure behavior. |
| `services/api/tests/test_p3_contracts.py` | Regression tests for p3 contracts, including success and failure behavior. |
| `services/api/tests/test_phase1_contracts.py` | Regression tests for phase1 contracts, including success and failure behavior. |
| `services/api/tests/test_phase2_continued.py` | Regression tests for phase2 continued, including success and failure behavior. |
| `services/api/tests/test_phase2_contracts.py` | Regression tests for phase2 contracts, including success and failure behavior. |
| `services/api/tests/test_security_hardening.py` | Regression tests for security hardening, including success and failure behavior. |
| `services/api/tests/test_uuid_ids.py` | Regression tests for uuid ids, including success and failure behavior. |
| `services/api/tests/test_websocket_auth.py` | Regression tests for websocket auth, including success and failure behavior. |
| `start.py` | Sets up isolated dependencies once, starts API/web/admin, checks readiness, and stops only its owned services. |
| `turbo.json` | Orders and caches workspace build/lint/type-check tasks while keeping tests fresh and development processes persistent. |
