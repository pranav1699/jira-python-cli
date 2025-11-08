from datetime import datetime
from jira import JIRA
import pandas as pd
import json 
import os




CONFIG_PATH = os.path.expanduser("~/.jira_config.json")
URl=""

def save_config(email, token, url):
    """Save Jira credentials locally."""
    config = {"email": email, "token": token, "url": url}
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)
    print(f"✅ Credentials saved to {CONFIG_PATH}")


def load_config():
    """Load Jira credentials if available."""
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError("⚠️ No config found. Set the credentials first.")
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def delete_config():
    """Delete Jira credentials file."""
    if os.path.exists(CONFIG_PATH):
        os.remove(CONFIG_PATH)
        print("🗑️ Deleted stored Jira credentials.")
    else:
        print("⚠️ No credentials found to delete.")


def view_config():
    """Show current stored Jira credentials (hides token)."""
    if not os.path.exists(CONFIG_PATH):
        print("⚠️ No credentials found. Set the credentials first.")
        return
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    masked_token = config["token"][:6] + "..." if "token" in config else "N/A"
    print(f"📘 Email: {config.get('email')}")
    print(f"🌐 URL: {config.get('url')}")
    print(f"🔑 Token: {masked_token}")


def auth_from_config():
    """Return an authenticated Jira client using saved credentials."""
    config = load_config()
    URL_CONFIG = config["url"]
    URL = URL_CONFIG
    return JIRA(
        basic_auth=(config["email"], config["token"]),
        server=config["url"]
    )

def auth() -> JIRA:
    return auth_from_config()

def search_issues(username: str = None, date: str = None, status: list[str] = None) -> pd.DataFrame:
    """
    Search Jira issues dynamically using optional filters:
    - username: Jira user email or name
    - date: created date (YYYY-MM-DD)
    - status: list of statuses (e.g., ["To Do", "In Progress"])
    """
    jira_client = auth_from_config()
    config = load_config()


    jql_parts = []

 
    if username:
        jql_parts.append(f'assignee = "{username}"')
    else:
        jql_parts.append('assignee = currentUser()')


    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")  # validate format
            jql_parts.append(f'created >= "{date}"')
        except ValueError:
            raise ValueError("❌ Date must be in YYYY-MM-DD format (YYYY-MM-DD)")

  
    if status:
        status_jql = " OR ".join([f'status = "{s}"' for s in status])
        jql_parts.append(f"({status_jql})")


    jql_query = " AND ".join(jql_parts) + " ORDER BY created DESC"


    fields = ["summary", "status", "issuetype", "duedate", "assignee", "reporter"]
    issues = jira_client.search_issues(jql_query, fields=fields, maxResults=500)


    issue_list = []
    for issue in issues:
        issue_list.append({
            "Key": issue.key,
            "Summary": issue.fields.summary,
            "Type": issue.fields.issuetype.name,
            "Status": issue.fields.status.name,
            "Assignee": issue.fields.assignee.displayName if issue.fields.assignee else None,
            "Reporter": issue.fields.reporter.displayName if issue.fields.reporter else None,
            "Due": issue.fields.duedate,
            "URL": f"{config['url']}/browse/{issue.key}",
        })

    df = pd.DataFrame(issue_list)
    return df

def create_issue(project_key: str, summary: str, description: str, issue_type: str = "Task"):
    jira_client = auth_from_config()
    new_issue = jira_client.create_issue(fields={
        "project": {"key": project_key},
        "summary": summary,
        "description": description,
        "issuetype": {"name": issue_type}
    })
    config = load_config()
    print(f"✅ Created issue {new_issue.key}: {config['url']}/browse/{new_issue.key}")
    return new_issue

def get_issue_key_by_summary(jira_client, project_key: str, summary: str):
    """Find Jira issue key by its summary text"""
    jql = f'project = "{project_key}" AND summary ~ "{summary}" ORDER BY created DESC'
    issues = jira_client.search_issues(jql, maxResults=1)
    if issues:
        return issues[0].key
    return None

def get_account_id(jira_client, assignee):
    """Convert email to Jira accountId (handles both email or ID safely)."""

    if assignee is None or pd.isna(assignee) or str(assignee).strip() == "":
        return None

    assignee = str(assignee).strip()


    if "@" not in assignee:
        return assignee

    try:
        users = jira_client.search_users(query=assignee, includeActive=True)
        if users:
            return users[0].accountId
        print(f"⚠️ Warning: Could not find user for {assignee}")
        return None
    except Exception as e:
        print(f"⚠️ Error fetching account ID for {assignee}: {e}")
        return None

def bulk_create_from_csv(csv_path: str, project_key: str):
    jira_client = auth_from_config()
    df = pd.read_csv(csv_path)
    print(f"📦 Creating {len(df)} issues from {csv_path}...")

    for _, row in df.iterrows():
        summary = row.get("summary") or "Untitled"
        description = row.get("description", "")
        issue_type = row.get("issuetype", "Task")
        parent_summary = row.get("parent", None)  
        assignee = row.get("assignee",None)

        parent_key = None
        if parent_summary:

            if pd.isna(parent_summary):
                parent_key = parent_summary
            else:
   
                parent_key = get_issue_key_by_summary(jira_client, project_key, parent_summary)

        fields = {
            "project": {"key": project_key},
            "summary": summary,
            "description": description,
            "issuetype": {"name": issue_type}
        }

        account_id = get_account_id(jira_client, assignee)
        if account_id:
            fields["assignee"] = {"id": account_id}

        if issue_type.lower() in ["sub-task", "subtask"] and parent_key:
            fields["parent"] = {"key": parent_key}

        issue = jira_client.create_issue(fields=fields)
        config = load_config()
        print(f"✅ Created {issue_type} {issue.key}: {config['url']}/browse/{issue.key}")