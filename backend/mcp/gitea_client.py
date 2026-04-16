"""
Gitea MCP Client — wraps the Gitea REST API (v1).
Gitea's API structure mirrors GitHub's API, making it a drop-in simulator
for GitHub Enterprise provisioning flows.
"""
import requests

from logger import get_logger

_log = get_logger(__name__)


class GiteaMCPClient:
    def __init__(self, base_url: str, admin_token: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {admin_token}",
            "Content-Type": "application/json",
        })

    def _api(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}/api/v1{path}"
        _log.debug("Gitea %s %s", method.upper(), path)
        resp = self.session.request(method, url, **kwargs)
        resp.raise_for_status()
        if resp.content:
            return resp.json()
        return {}

    # ------------------------------------------------------------------
    # Organization / team membership
    # ------------------------------------------------------------------

    def create_org_if_missing(self, org_name: str) -> dict:
        try:
            return self._api("GET", f"/orgs/{org_name}")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return self._api("POST", "/orgs", json={
                    "username": org_name,
                    "visibility": "private",
                })
            raise

    def get_or_create_team(self, org_name: str, team_name: str) -> dict:
        teams = self._api("GET", f"/orgs/{org_name}/teams")
        for t in teams:
            if t["name"] == team_name:
                return t
        return self._api("POST", f"/orgs/{org_name}/teams", json={
            "name": team_name,
            "permission": "write",
            "units": ["repo.code", "repo.issues", "repo.pulls"],
        })

    def add_user_to_team(self, team_id: int, username: str) -> dict:
        return self._api("PUT", f"/teams/{team_id}/members/{username}")

    def is_user_in_team(self, team_id: int, username: str) -> bool:
        try:
            self._api("GET", f"/teams/{team_id}/members/{username}")
            return True
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return False
            raise

    # ------------------------------------------------------------------
    # Provisioning entry point
    # ------------------------------------------------------------------

    def provision(self, org: str, team: str, username: str) -> dict:
        _log.info("Gitea provision | org=%s | team=%s | username=%s", org, team, username)
        self.create_org_if_missing(org)
        team_obj = self.get_or_create_team(org, team)
        self.add_user_to_team(team_obj["id"], username)
        verified = self.is_user_in_team(team_obj["id"], username)
        _log.info("Gitea provision complete | username=%s | team_added=%s", username, verified)
        return {
            "system": "gitea",
            "org": org,
            "team": team,
            "username": username,
            "team_added": verified,
        }

    def verify_access(self, org: str, team: str, username: str) -> bool:
        _log.debug("Gitea verify access | org=%s | team=%s | username=%s", org, team, username)
        try:
            teams = self._api("GET", f"/orgs/{org}/teams")
            for t in teams:
                if t["name"] == team:
                    result = self.is_user_in_team(t["id"], username)
                    _log.info("Gitea access verification | username=%s | verified=%s", username, result)
                    return result
            _log.warning("Gitea team not found | org=%s | team=%s", org, team)
            return False
        except Exception as e:
            _log.error("Gitea verify_access error: %s", e)
            return False
