# Contributing to AI Agent Product Design Lab

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. **Fork the repository**
2. **Clone your fork**: `git clone <your-fork-url>`
3. **Set up development environment**: See [Setup Guide](docs/implementation/setup-guide.md)
4. **Create a branch**: `git checkout -b feature/your-feature-name`

## Development Guidelines

### Code Style

**Frontend (TypeScript/React)**
- Use TypeScript for all new code
- Follow React best practices (hooks, functional components)
- Use Prettier for formatting: `npm run format`
- Run ESLint: `npm run lint`

**Backend (Python)**
- Follow PEP 8 style guide
- Use Black for formatting: `black .`
- Use type hints for all functions
- Run Ruff for linting: `ruff check .`

### Commit Messages

Follow conventional commits format:

```
type(scope): subject

body (optional)

footer (optional)
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(canvas): add drag-to-connect functionality
fix(api): handle missing agent_id in links endpoint
docs(readme): update setup instructions
```

### Pull Request Process

1. **Update documentation**: If your change affects user-facing features or architecture
2. **Add tests**: Include tests for new features or bug fixes
3. **Update CHANGELOG**: Add entry describing your changes
4. **Ensure tests pass**: Run test suite before submitting
5. **Write clear description**: Explain what and why, not just how

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How have you tested these changes?

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added/updated
- [ ] All tests pass
```

## Documentation

- **Code comments**: Explain "why", not "what"
- **README updates**: Update main README if setup changes
- **Architecture docs**: Update `docs/implementation/` for architectural changes
- **API docs**: Update `docs/implementation/api-design.md` for API changes

## Testing

### Frontend Tests

```bash
cd frontend
npm test
```

### Backend Tests

```bash
cd backend
pytest
```

### Manual Testing Checklist

Before submitting PR:
- [ ] Test in local development environment
- [ ] Test on different browsers (if frontend change)
- [ ] Test error cases and edge cases
- [ ] Verify no console errors

## Bug Reports

When reporting bugs, include:

1. **Description**: Clear description of the issue
2. **Steps to reproduce**: Detailed steps
3. **Expected behavior**: What should happen
4. **Actual behavior**: What actually happens
5. **Environment**: OS, Node version, Python version
6. **Screenshots**: If applicable

## Feature Requests

When requesting features:

1. **Use case**: Why is this feature needed?
2. **Proposed solution**: How should it work?
3. **Alternatives considered**: Other approaches you've thought about
4. **Additional context**: Any other relevant information

## Questions?

- Open an issue for questions or discussions
- Check existing issues and PRs first
- Be respectful and constructive in all communications

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Respect differing opinions and approaches

Thank you for contributing! 🎉

