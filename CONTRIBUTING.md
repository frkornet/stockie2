# Contributing to Stockie

Welcome to the Stockie Financial Analysis Platform! This document outlines the development standards, testing requirements, and contribution guidelines for the project.

## 📋 **Development Overview**

Stockie uses a hybrid architecture where Python data pipelines feed a PostgreSQL database, and C++ services provide high-performance data access. These components are decoupled - they communicate through the database rather than direct code integration.

## 🐍 **Python Development Standards**

### **Code Requirements**
- **Type Hints**: Required for all function parameters, return values, and class attributes
- **Testing Framework**: pytest for all unit and integration tests
- **Coverage Requirement**: Minimum 85% code coverage
- **Testing Policy**: Unit tests must be included and passing before any branch changes

### **Code Style** (Under Research)
- Python coding style standards are currently being evaluated
- Options under consideration: PEP 8, Black formatter, Google Python Style Guide
- Final standards will be documented here once selected

### **Documentation**
- Docstring format: TBD (Google/NumPy/Sphinx style under consideration)
- Type hints serve as inline documentation
- Complex algorithms require detailed docstring explanations

## 🔧 **C++ Development Standards**

### **Build System Evolution**
- **Phase 2-3**: Traditional Makefiles for simplicity and direct control
- **Phase 4+**: Evaluation of CMake (industry standard) vs. Meson (simpler syntax)
- Build system may evolve as project complexity increases

### **Testing Framework**
- **Google Test (gtest)**: Primary testing framework under consideration
- **Alternative**: Catch2 (header-only, simpler setup)
- **Coverage Requirement**: Minimum 85% code coverage
- **Testing Policy**: Unit tests required before any branch changes

### **Code Style** (Under Research)
- C++ coding style standards are currently being evaluated
- Options under consideration: Google C++ Style Guide, LLVM Coding Standards, ISO C++ Core Guidelines
- Final standards will be documented here once selected

## 🗃️ **Database Standards**

### **Schema Changes**
- All database schema changes must include migration scripts
- Backward compatibility required for data pipeline continuity
- Performance impact assessment for large datasets (8,000+ tickers)

### **Testing**
- Database integration tests for both Python pipelines and C++ services
- Test data should represent realistic financial data volumes
- Performance benchmarks for critical queries

## 🧪 **Testing Requirements**

### **Coverage Standards**
- **Minimum**: 85% code coverage for both Python and C++ codebases
- **Financial Calculations**: Consider higher coverage (90%+) for money-related algorithms
- **Branch Coverage**: Include branch coverage in addition to line coverage
- **Exception Handling**: Test error paths and edge cases

### **Test Organization**
- **Python**: `tests/` directory structure mirroring `src/` structure
- **C++**: Test files alongside source files or separate `tests/` directory
- **Integration Tests**: Database-focused tests for pipeline-to-service data flow
- **Performance Tests**: Benchmarks for critical financial calculations

### **Test Data**
- Use realistic but anonymized financial data for testing
- Include edge cases (market crashes, missing data, extreme values)
- Test with various time ranges (1 month to 20+ years of data)

## 🚀 **Development Workflow**

### **Before Making Changes**
1. Create feature branch from `main`
2. Write unit tests for new functionality
3. Ensure all existing tests pass
4. Verify minimum coverage requirements
5. Update documentation if needed

### **Code Review Requirements**
- All changes require review before merging
- Reviewer must verify test coverage and test quality
- Performance impact assessment for data-intensive changes
- Security review for financial data handling

### **Commit Standards**
- Clear, descriptive commit messages
- Reference issue numbers when applicable
- Atomic commits (one logical change per commit)

## 📚 **Documentation Standards**

### **Code Documentation**
- **Python**: Docstrings for all public functions, classes, and modules
- **C++**: Documentation format TBD (Doxygen under consideration)
- **Financial Algorithms**: Detailed explanations including mathematical formulas
- **API Documentation**: Clear parameter and return value descriptions

### **Project Documentation**
- Keep README.md, ARCHITECTURE_ROADMAP.md, and AUTHORS.md updated
- Document architectural decisions and trade-offs
- Update installation and setup instructions as they evolve

## 🔐 **Security & Financial Data**

### **Data Handling**
- No real financial account information in code or tests
- Use mock/synthetic data for development and testing
- Follow data privacy best practices
- Educational disclaimers required for all trading/investment features

### **Dependencies**
- Regular security updates for all dependencies
- Careful evaluation of new dependencies, especially for financial calculations
- Document rationale for major dependency choices

## 🤝 **Getting Help**

### **Development Questions**
- Check existing documentation first (README.md, ARCHITECTURE_ROADMAP.md)
- Review existing code patterns and tests
- Open GitHub issues for technical discussions

### **Standards Evolution**
- Development standards will evolve as the project matures
- Community input welcome on standards selection
- Changes to standards will be communicated clearly and documented

---

## 📝 **Current Status**

This document represents the current development approach. Several standards are still under research:

**To Be Determined:**
- Python code style guide selection
- C++ code style guide selection  
- C++ build system final choice (Phase 4+)
- Documentation format standards

**Confirmed Standards:**
- Python type hints (required)
- pytest for Python testing
- 85% minimum code coverage
- Unit tests required before code changes
- Database-mediated architecture (no direct Python/C++ integration)

---

*This document will be updated as development standards are finalized and the project evolve.*