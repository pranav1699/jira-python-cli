# jira_python — CLI for Jira

Small CLI tool to manage Jira issues from your terminal. Implements commands to store credentials, list issues, create single issues, and bulk-create from CSV.

## Requirements
- Python 3.8+
- Packages:
  - jira
  - pandas
  - typer
  - rich

Install:
```
pip install jira pandas typer rich
```

## Quick setup
1. Save your credentials (email, API token, Jira site URL):
```
python main.py user set
```
2. View or delete stored credentials:
```
python main.py user view
python main.py user delete
```

## Authentication check
```
python main.py whoami
```

## Commands

- **List issues**
```
python main.py list [--user USER] [--date YYYY-MM-DD] [--status STATUS...] [--due-now] [--export]
```
  Notes:
  - If `--user` is omitted, it lists issues for the current authenticated user.
  - `--date` filters by `created >= YYYY-MM-DD`.
  - `--status` accepts multiple values (e.g., `--status "To Do" --status "In Progress"`).
  - `--due-now` shows issues due today or overdue.
  - `--export` writes a CSV of the filtered results.

  Examples:
```
# My open issues created since 2024-01-01
python main.py list --date 2024-01-01

# Issues assigned to alice@example.com in "In Progress"
python main.py list -u alice@example.com -s "In Progress"

# Export issues for current user
python main.py list --export
```

- **Create a single issue**
```
python main.py create --project PROJ --summary "Short summary" [--description "desc"] [--type Task]
```

- **Bulk create from CSV**
```
python main.py bulk --csv /path/to/issues.csv --project PROJ
```
  CSV header example:
```
summary,description,issuetype,parent,assignee
"Task A","Desc","Task",,
"Subtask 1","Subtask of A","Sub-task","Task A","user@example.com"
```
  Notes:
  - `parent` is optional and should match an existing issue summary to attach a sub-task.
  - `assignee` can be an email; the tool will try to resolve it to a Jira accountId.

## Troubleshooting
- If you see "No config found", run `python main.py user set` to save credentials.
- Date filter format must be YYYY-MM-DD.
- Adjust Jira API permissions or token scope if you cannot create or assign issues.

## License / Notes
- This is a small helper tool — adapt it to your workflow and Jira instance.
