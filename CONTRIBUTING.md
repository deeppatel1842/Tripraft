# Contributing to Tripraft

Thank you for considering contributing to Tripraft! This document provides guidelines for contributing to the project.

---

## 🤝 How to Contribute

### 1. Fork the Repository

```bash
# Fork via GitHub UI, then clone your fork
git clone git@github.com:YOUR_USERNAME/Tripraft.git
cd Tripraft
```

### 2. Create a Branch

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Or a bugfix branch
git checkout -b fix/bug-description
```

### 3. Make Your Changes

- Write clean, readable code
- Follow existing code style
- Add comments for complex logic
- Update documentation if needed

### 4. Test Your Changes

```bash
# Backend tests
cd web/backend
python -m pytest

# Frontend tests
cd web/frontend
npm test

# Manual testing
python web/backend/run.py
npm run dev
```

### 5. Commit Your Changes

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```bash
# Feature
git commit -m "feat: Add new expense split type"

# Bug fix
git commit -m "fix: Resolve cache invalidation issue"

# Documentation
git commit -m "docs: Update API reference"

# Performance
git commit -m "perf: Optimize balance calculation"

# Refactor
git commit -m "refactor: Simplify cache operations"
```

### 6. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request via GitHub UI
# - Describe your changes
# - Reference related issues
# - Add screenshots if UI changes
```

---

## 📋 Code Standards

### Python (Backend)

**Style Guide:** [PEP 8](https://pep8.org/)

```python
# Good
def calculate_balance(group_id: str, user_id: str) -> float:
    """
    Calculate user balance in a group.
    
    Args:
        group_id: The group identifier
        user_id: The user identifier
        
    Returns:
        User's net balance (positive = owed, negative = owes)
    """
    # Implementation
    return balance

# Use type hints
# Write docstrings
# Keep functions < 50 lines
# Use meaningful variable names
```

**Tools:**
- `black` - Code formatter
- `pylint` - Linter
- `mypy` - Type checker

```bash
# Format code
black web/backend/

# Check style
pylint web/backend/

# Type check
mypy web/backend/
```

### JavaScript/React (Frontend)

**Style Guide:** [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)

```javascript
// Good
const ExpenseCard = ({ expense, onDelete }) => {
  const [isDeleting, setIsDeleting] = useState(false);
  
  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onDelete(expense.id);
    } catch (error) {
      console.error('Delete failed:', error);
    } finally {
      setIsDeleting(false);
    }
  };
  
  return (
    <div className="expense-card">
      {/* Component JSX */}
    </div>
  );
};

// Use functional components
// Use hooks properly
// Write PropTypes or TypeScript
// Keep components < 200 lines
```

**Tools:**
- `eslint` - Linter
- `prettier` - Code formatter

```bash
# Format code
npm run format

# Check style
npm run lint

# Fix issues
npm run lint:fix
```

---

## 🏗️ Project Structure

### Adding New Features

#### Backend (Python)

**1. Create Route File**
```bash
# Location: web/backend/expense_engine/routes/
touch web/backend/expense_engine/routes/new_feature_routes.py
```

**2. Add Route Handlers**
```python
from flask import Blueprint, request, jsonify
from ..service import expense_service
from ..security.rbac import require_permission

bp = Blueprint('new_feature', __name__)

@bp.route('/feature', methods=['POST'])
@require_permission('member')
def create_feature():
    """Create new feature."""
    data = request.get_json()
    result = expense_service.create_feature(data)
    return jsonify(result), 201
```

**3. Register Blueprint**
```python
# In web/backend/expense_engine/__init__.py
from .routes import new_feature_routes

def create_app():
    app = Flask(__name__)
    app.register_blueprint(new_feature_routes.bp, url_prefix='/api/expense')
    return app
```

**4. Update Service Layer**
```python
# In web/backend/expense_engine/service.py
class ExpenseService:
    def create_feature(self, data):
        # Business logic
        # Cache operations
        # Database operations
        return result
```

#### Frontend (React)

**1. Create Component**
```bash
# Location: web/frontend/src/components/
touch web/frontend/src/components/NewFeature.jsx
```

**2. Implement Component**
```javascript
import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';

export const NewFeature = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['feature'],
    queryFn: () => axios.get('/api/expense/feature')
  });
  
  const mutation = useMutation({
    mutationFn: (data) => axios.post('/api/expense/feature', data),
    onSuccess: () => {
      // Invalidate queries
    }
  });
  
  return (
    <div>
      {/* Component UI */}
    </div>
  );
};
```

**3. Add Route**
```javascript
// In web/frontend/src/App.jsx
import { NewFeature } from './components/NewFeature';

<Route path="/feature" element={<NewFeature />} />
```

---

## 🧪 Testing Guidelines

### Backend Tests

```python
# tests/test_expense_service.py
import pytest
from expense_engine.service import expense_service

def test_create_expense():
    """Test expense creation."""
    expense = expense_service.create_expense(
        description="Test",
        amount=100.0,
        paid_by="user1",
        splits=[{"user_id": "user1", "amount": 50}]
    )
    
    assert expense['amount'] == 100.0
    assert len(expense['splits']) == 1

def test_balance_calculation():
    """Test balance calculation."""
    balance = expense_service.get_balance("user1", "group1")
    assert isinstance(balance, float)
```

### Frontend Tests

```javascript
// src/components/__tests__/ExpenseCard.test.jsx
import { render, screen, fireEvent } from '@testing-library/react';
import { ExpenseCard } from '../ExpenseCard';

describe('ExpenseCard', () => {
  it('renders expense details', () => {
    const expense = {
      id: '1',
      description: 'Dinner',
      amount: 100
    };
    
    render(<ExpenseCard expense={expense} />);
    expect(screen.getByText('Dinner')).toBeInTheDocument();
    expect(screen.getByText('$100')).toBeInTheDocument();
  });
  
  it('handles delete action', async () => {
    const onDelete = jest.fn();
    const expense = { id: '1', description: 'Test' };
    
    render(<ExpenseCard expense={expense} onDelete={onDelete} />);
    fireEvent.click(screen.getByText('Delete'));
    
    expect(onDelete).toHaveBeenCalledWith('1');
  });
});
```

---

## 📝 Documentation

### Update Documentation When:

- **Adding API endpoints** → Update `web/backend/expense_engine/docs/API_REFERENCE.md`
- **Changing architecture** → Update `web/backend/expense_engine/docs/ARCHITECTURE_FLOWS.md`
- **Adding features** → Update respective module README
- **Fixing bugs** → Update `CHANGELOG.md`

### Documentation Standards

```markdown
## API Endpoint

### POST /api/expense/feature

**Description:** Creates a new feature.

**Authentication:** Required (JWT Bearer token)

**Permission:** member, admin, owner

**Request Body:**
\`\`\`json
{
  "name": "Feature Name",
  "description": "Feature description"
}
\`\`\`

**Response (201 Created):**
\`\`\`json
{
  "id": "feature_id",
  "name": "Feature Name",
  "created_at": "2025-01-01T00:00:00Z"
}
\`\`\`

**Errors:**
- `400` - Invalid request data
- `401` - Unauthorized
- `403` - Insufficient permissions
```

---

## 🐛 Bug Reports

### Before Reporting

1. Check existing issues
2. Try latest version
3. Reproduce consistently
4. Gather error logs

### Bug Report Template

```markdown
**Bug Description:**
Clear description of the bug

**Steps to Reproduce:**
1. Go to '...'
2. Click on '...'
3. See error

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Environment:**
- OS: Windows 10
- Python: 3.11
- Node: 18.17
- Browser: Chrome 120

**Logs:**
\`\`\`
Error logs here
\`\`\`

**Screenshots:**
If applicable
```

---

## 💡 Feature Requests

### Feature Request Template

```markdown
**Feature Description:**
Clear description of the feature

**Problem It Solves:**
What problem does this solve?

**Proposed Solution:**
How should it work?

**Alternatives Considered:**
Other approaches you've thought about

**Additional Context:**
Any other information
```

---

## ✅ Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages follow Conventional Commits
- [ ] No merge conflicts with main branch
- [ ] PR description explains changes
- [ ] Screenshots included (if UI changes)
- [ ] Related issues referenced

---

## 📞 Getting Help

- **Documentation:** Check [docs/](docs/) folder
- **Issues:** Search existing issues first
- **Discussions:** Use GitHub Discussions for questions
- **Email:** support@tripraft.com (for sensitive issues)

---

## 🎯 Priority Areas

We especially welcome contributions in:

1. **Testing** - Unit tests, integration tests
2. **Documentation** - Tutorials, guides, examples
3. **Performance** - Optimization, caching improvements
4. **Security** - Vulnerability fixes, security features
5. **UI/UX** - Frontend improvements, accessibility
6. **Mobile** - React Native app development

---

## 📜 Code of Conduct

### Our Standards

- **Be respectful** - Treat everyone with respect
- **Be constructive** - Provide helpful feedback
- **Be patient** - Remember we're all learning
- **Be inclusive** - Welcome diverse perspectives

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Personal attacks
- Publishing private information
- Unprofessional conduct

### Enforcement

Violations may result in:
1. Warning
2. Temporary ban
3. Permanent ban

Report issues to: conduct@tripraft.com

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the same license as the project (Proprietary).

---

**Thank you for contributing to Tripraft! 🌍✨**
