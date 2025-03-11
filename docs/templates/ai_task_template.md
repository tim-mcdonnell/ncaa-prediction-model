# AI Task Template

## Task Title: [Concise, specific title of the task]

> [One-sentence summary of what needs to be implemented]

## Context

[Brief explanation of why this task is needed and how it fits into the larger project]

## Technical Background

- **Component**: [Which part of the system this relates to, e.g., "Collection Pipeline"]
- **Related Files**: 
  - `src/path/to/relevant/file.py`
  - `tests/path/to/test_file.py`
- **Dependencies**: [Any other components this interacts with]

## Requirements

### Functional Requirements

- [ ] [Specific, testable requirement 1]
- [ ] [Specific, testable requirement 2]
- [ ] [Specific, testable requirement 3]

### Technical Requirements

- [ ] Follow the [Test-Driven Development approach](../development/test-strategy.md)
- [ ] Use [Polars](https://pola.rs/) for any data manipulation
- [ ] Implement proper error handling using the resilience patterns
- [ ] Add appropriate type annotations
- [ ] Update relevant documentation if needed

### Implementation Details

```python
# Pseudo-code or code skeleton to guide implementation
def function_to_implement(param1, param2):
    # Expected behavior:
    # 1. Validate inputs
    # 2. Process data
    # 3. Return result
    pass
```

## Acceptance Criteria

- [ ] All tests pass (`uv python -m pytest tests/path/to/test_file.py -v`)
- [ ] Code follows the [modularity guidelines](../development/modularity-guidelines.md)
- [ ] Implementation maintains the [pipeline architecture](../development/pipeline-architecture.md)
- [ ] No regression in existing functionality

## Constraints

- Must maintain backward compatibility with [specific component]
- Should complete within [time constraint if applicable]
- Performance considerations: [any specific performance requirements]

## Resources

- [Link to relevant documentation]
- [Link to similar implementation for reference]
- [Any other helpful resources]

## Questions for Clarification

- [Anticipated questions the AI might have]
- [Areas where ambiguity might exist]

---

> **Note for AI Agent**: Before starting implementation, confirm your understanding of the task and clarify any ambiguities. Follow the pipeline architecture and patterns established in the codebase. 