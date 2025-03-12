# NCAA Basketball Prediction Model Documentation Standards

This directory contains examples that serve as the standards for project documentation. All document types follow these examples to ensure consistency, clarity, and effectiveness in our development process.

## Documentation Approach

We follow an **example-based approach** rather than using abstract templates. The examples demonstrate the expected structure, content, and style for different document types.

## Available Examples

| Document Type | Purpose | Example Location | When to Use |
|---------------|---------|------------------|-------------|
| Milestone | Define project milestones | [Example](ai_milestone_example.md) | When planning a major project phase |
| AI Task | Guide AI agents on implementation | [Example](ai_task_example.md) | When assigning tasks to AI |
| Issue | Track bugs and improvement requests | [Example](ai_issue_example.md) | When identifying problems |
| PR | Document code changes | [Example](ai_pr_example.md) | When submitting code for review |

## Key Documentation Principles

1. **Be Concise**: Focus on essential information
2. **Be Specific**: Include concrete details, not vague descriptions
3. **Be Actionable**: Ensure documentation leads to clear actions
4. **Be Visual**: Use diagrams and examples where helpful
5. **Be Consistent**: Follow established patterns

## Documentation Workflow

### For Milestones
1. Use the milestone example as a reference for content and structure
2. Create milestones directly on GitHub at https://github.com/tim-mcdonnell/ncaa-prediction-model/milestones
3. Include all the key information from the example such as objectives, deliverables, and acceptance criteria

### For AI Tasks
1. Copy the AI task example from `docs/examples/ai_task_example.md`
2. Update all sections to reflect the specific task
3. Add concrete examples that show expected inputs and outputs

### For Issues & PRs
1. Refer to the examples (`ai_issue_example.md` and `ai_pr_example.md`) when creating GitHub issues and PRs
2. Use the GitHub interface to create new issues and PRs, following the established format
3. Include all relevant sections from the examples to ensure comprehensive documentation

## Example Maintenance

Our examples evolve as our project matures. If you have suggestions for improvements:

1. Create an issue describing the proposed changes
2. Implement the changes in a PR
3. Update any related documentation

Remember: The goal of documentation is to facilitate development, not create bureaucracy. Examples should be practical and demonstrate real-world usage patterns that have proven effective in our project.

## Additional Resources

For more guidance on working with AI coding agents, see:

- [AI Coding Agent Guide](../development/ai-coding-agent-guide.md) - General guidance for AI agents
- [AI Task Authoring Guide](../development/ai-task-authoring-guide.md) - Best practices for creating effective AI tasks

## Adding New Examples

When adding new examples to this directory:

1. Create your example file with a clear, descriptive name (e.g., `pipeline_usage_example.md`)
2. Add a link to your example in this index file
3. Include sufficient context and explanation in your example
4. Reference the example from relevant documentation 