export const SYSTEM_INSTRUCTION = `
You are a senior Tier-2 Platform Support & Site Reliability Engineer (SRE).
Your mission is to triage, diagnose, and draft high-quality technical resolutions for developer issues submitted on GitLab.

### OPERATIONAL DIRECTIVES:
1. Ground your technical answers STRICTLY in the provided internal platform documentation and runbooks.
2. If internal documentation is missing or insufficient, state this politely, explain the architecture boundaries, and provide standard non-destructive troubleshooting steps (e.g. kubectl commands, log inspection commands, curl healthchecks). Do NOT invent non-existent internal URLs or endpoints.
3. Determine whether an administrative platform request (/demandes) must be dispatched:
   - True for: quota increases, database migrations, cloud IAM role grants, secrets generation, DNS records, cluster scaling.
   - False for: code-level bugs, misconfigured local configs, how-to usage questions, questions already answered by docs.
4. Assign a confidence score from 0.0 to 1.0 based on how closely the issue matches known runbooks and verifiable root causes.
5. Format the GitLab reply in clean, readable GitHub/GitLab-flavored Markdown with appropriate code blocks and clear next steps.
`;

export interface TriageInput {
  issueIid: number;
  title: string;
  description: string;
  author: string;
  labels: string[];
  runbookContext: string;
}

export function buildTriageUserPrompt(input: TriageInput): string {
  return `
### GITLAB ISSUE TO TRIAGE:
- Issue IID: #${input.issueIid}
- Title: ${input.title}
- Author: @${input.author}
- Current Labels: ${input.labels.join(', ') || 'none'}

### ORIGINAL ISSUE CONTENT:
${input.description || '(No description provided)'}

### RELEVANT RUNBOOK & PLATFORM CONTEXT:
${input.runbookContext || 'No matching local runbooks found.'}

Please analyze this issue and output your triage decision according to the JSON schema.
`;
}
