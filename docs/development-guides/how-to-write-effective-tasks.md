---
title: How to Write Effective Tasks for AI Coding Agents
description: Guidelines for creating clear, comprehensive task descriptions for AI coding agents in the NCAA Basketball Analytics Project
---

# How to Write Effective Tasks for AI Coding Agents

## Introduction

This guide outlines best practices for writing clear, comprehensive task descriptions for AI coding agents. Following these guidelines will help ensure that your AI assistant correctly understands, implements, and validates your coding requirements.

## Core Principles

### 1. Be Explicit, Not Implicit
- State requirements directly rather than assuming the AI will infer them
- Include exact file paths, naming conventions, and structural requirements
- Avoid vague terminology or ambiguous directions

### 2. Structure for Discoverability
- Use clear section headings that signal their purpose
- Apply consistent formatting and visual hierarchy
- Employ checklists and code blocks for clarity
- Use emoji icons to distinguish different sections visually

### 3. Emphasize Verification
- Include explicit testing requirements with specific test cases
- Require real-world validation, not just unit tests
- Provide concrete verification steps for checking implementation
- Define clear acceptance criteria

### 4. Prioritize Architecture Alignment
- Explicitly define architectural requirements and constraints
- Specify database structures, file organization, and design patterns
- Prevent misalignment by stating what NOT to do when necessary
- Reference existing architecture documentation

## Essential Task Components

### 🎯 Task Overview Section
- Title: Clear, concise description of the task
- Background: Context explaining why this task matters
- Objective: Specific outcome to achieve
- Scope: Explicit boundaries of what should/shouldn't be implemented

### 📐 Technical Requirements Section
- Architecture requirements with specific file paths and naming conventions
- Database schema with actual SQL statements
- API endpoints with exact routes and response formats
- Dependencies and external integrations
- Performance and security considerations

### 🧪 Testing Framework Section
- Test-Driven Development (TDD) approach with RED-GREEN-REFACTOR steps
- Specific test cases with names and expected outcomes
- Unit testing requirements
- Integration testing requirements
- Real-world data testing instructions

### 📄 Documentation Requirements Section
- Files to create or update
- Required content for documentation
- Code commenting standards
- Examples or templates to follow

### 🛠️ Implementation Process Section
- Step-by-step workflow
- Breakdown of implementation phases
- Dependencies between steps
- Verification checkpoints

### ✅ Acceptance Criteria Section
- Explicit list of requirements that must be met
- Testing success parameters
- Performance benchmarks
- Documentation completeness
- Code quality standards

## Task Template Structure

```markdown
# Task: [Descriptive Title]

## 📋 Overview
**Background:** [Context and why this matters]
**Objective:** [Specific goal to accomplish]
**Scope:** [Clear boundaries of the task]

## 📐 Technical Requirements
### Architecture
- [Specific structural requirements]
- [File paths and naming conventions]
- [Design patterns to follow]

### Database
```sql
-- Exact schema definition
CREATE TABLE example (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);
```

### API Design
- Endpoint: `[Exact endpoint path]`
- Method: `[HTTP method]`
- Request/Response format: [Provide exact format]

## 🧪 Testing Requirements
### Test Cases
- [ ] Test `test_name_1`: [Description of test case]
- [ ] Test `test_name_2`: [Description of test case]

### TDD Process
1. **RED**: Write failing tests first
2. **GREEN**: Implement minimum code to pass tests
3. **REFACTOR**: Clean up code while maintaining passing tests

### Real-World Testing
- Run: `[Exact command to execute]`
- Verify: [Specific outcomes to check]

## 📄 Documentation Requirements
- [ ] Update `README.md` with [specific sections]
- [ ] Create API documentation for new endpoints
- [ ] Add implementation notes in [specific location]

## 🛠️ Implementation Process
1. [First step with details]
2. [Second step with details]
3. [Remaining steps...]

## ✅ Acceptance Criteria
- [ ] All specified tests pass
- [ ] Code follows project architecture
- [ ] Real-world testing validates functionality
- [ ] Documentation is complete and accurate
- [ ] Code meets quality standards (specify tools/metrics)
```

## Common Pitfalls to Avoid

### ❌ Vague Requirements
**Poor:** "Implement data storage for NCAA information."  
**Better:** "Create a single DuckDB database file at `data/ncaa.duckdb` with the schema defined in the Technical Requirements section."

### ❌ Unspecific Testing Instructions
**Poor:** "Write tests for the implementation."  
**Better:** "Implement the following test cases in `tests/test_ncaa_data.py`:
- `test_fetch_data_success`: Verifies successful API data retrieval
- `test_store_data_formatting`: Ensures data is properly formatted before storage"

### ❌ Ambiguous Architecture Guidance
**Poor:** "Follow the project's database architecture."  
**Better:** "Use a single DuckDB database file at `data/ncaa.duckdb`. Do NOT create separate database files for different data types. All tables should be created in this single file."

### ❌ Missing Verification Steps
**Poor:** "Make sure it works."  
**Better:** "Execute `python -m ncaa.scripts.fetch --start-date 2023-01-01 --end-date 2023-01-31` and verify that:
1. Data is retrieved without errors
2. The database file contains the expected number of records
3. The console output matches the expected format"

## Implementation Verification Checklist

Before considering a task complete, verify that:

1. **Tests:**
   - [ ] All specified tests are implemented
   - [ ] Tests run before implementation (RED)
   - [ ] Implementation passes all tests (GREEN)
   - [ ] Code is refactored while maintaining passing tests (REFACTOR)
   - [ ] Real-world testing with actual data confirms functionality

2. **Architecture:**
   - [ ] Implementation follows specified architecture
   - [ ] File paths and naming conventions match requirements
   - [ ] Database schema matches specifications
   - [ ] No architecture anti-patterns are introduced

3. **Documentation:**
   - [ ] All required documentation is created/updated
   - [ ] Implementation decisions are documented
   - [ ] API documentation is complete
   - [ ] Code includes appropriate comments

4. **Verification:**
   - [ ] All verification steps are executed
   - [ ] Results match expected outcomes
   - [ ] Edge cases are tested
   - [ ] Performance meets requirements

## Conclusion

Writing effective tasks for AI coding agents requires clarity, specificity, and thoroughness. By following these guidelines and using the provided template, you can ensure that your AI assistant has all the information needed to successfully implement your requirements.

Remember that AI agents work best with explicit instructions that leave little room for interpretation. Taking the time to craft comprehensive task descriptions will save development time, reduce misunderstandings, and result in higher-quality implementations.