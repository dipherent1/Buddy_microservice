import os
import sys
from pathlib import Path
from typing import Any, Optional

from app.core.logger import logging
from google.auth.transport.requests import Request
from google.auth.credentials import Credentials as BaseCredentials
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# OAuth 2.0 scopes for Google Docs and Drive
logger = logging.getLogger(__name__)
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.readonly'
]

TOKEN_PATH = Path(__file__).parent / 'tokens' / 'token.json'
CREDENTIALS_PATH = Path(__file__).parent / 'tokens' / 'credentials.json'

logger.info(f"Using TOKEN_PATH: {TOKEN_PATH}, CREDENTIALS_PATH: {CREDENTIALS_PATH}")
# Load environment variables from a local .env if present
def _load_env_file() -> None:
    env_file = Path(__file__).parent / ".env"
    try:
        from dotenv import load_dotenv  # type: ignore
        # Only load if file exists; don't override existing environment
        if env_file.exists():
            load_dotenv(dotenv_path=env_file, override=False)
    except Exception:
        # Fallback simple parser if python-dotenv isn't installed
        if env_file.exists():
            try:
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    k, v = line.split('=', 1)
                    if k and k not in os.environ:
                        os.environ[k] = v
            except Exception:
                pass

_load_env_file()

class GoogleDocsService:
    """Handles Google Docs API operations with OAuth authentication"""
    
    def __init__(self):
        # Use the broad base credentials interface to satisfy all concrete types
        self.creds: Optional[BaseCredentials] = None
        # Lazily constructed Google API clients; annotate as Any to appease type checker
        self.docs_service: Any = None
        self.drive_service: Any = None
        self.sheets_service: Any = None

    def _get_credentials_path(self) -> Path:
        """Resolve OAuth client secrets path.

        Priority:
        1) GOOGLE_CREDENTIALS_PATH env var (file path)
        2) credentials.json alongside this server.py
        """
        env_path = os.environ.get("GOOGLE_CREDENTIALS_PATH")
        if env_path:
            # Return the env-provided path even if missing, so errors surface the intended location
            return Path(env_path)
        return CREDENTIALS_PATH
        
    def authenticate(self) -> bool:
        """
        Authenticate user using OAuth 2.0 flow.
        Returns True if authentication successful.
        """
        # Load existing credentials if available
        if TOKEN_PATH.exists():
            # from_authorized_user_file returns oauth2.credentials.Credentials which implements BaseCredentials
            self.creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        
        # Refresh or initiate OAuth flow
        if not self.creds or not self.creds.valid:
            if self.creds and getattr(self.creds, "expired", False) and getattr(self.creds, "refresh_token", None):
                self.creds.refresh(Request())
            else:
                cred_path = self._get_credentials_path()
                if not cred_path.exists():
                    env_hint = os.environ.get("GOOGLE_CREDENTIALS_PATH")
                    msg = [
                        "Credentials file not found.",
                        f"Looked forz: {cred_path}",
                    ]
                    if env_hint:
                        msg.append("GOOGLE_CREDENTIALS_PATH is set but the file was not found at that path.")
                    msg.append(
                        "Set GOOGLE_CREDENTIALS_PATH to your OAuth client secrets JSON path, "
                        f"or place a 'credentials.json' next to this server at: {CREDENTIALS_PATH}"
                    )
                    raise FileNotFoundError("\n".join(msg))

                flow = InstalledAppFlow.from_client_secrets_file(str(cred_path), SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # Save credentials for next time
            TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            if self.creds and hasattr(self.creds, "to_json"):
                with open(TOKEN_PATH, 'w') as token:
                    token.write(getattr(self.creds, "to_json")())
            else:
                # Some credential types may not support to_json; skip caching in that rare case
                print("Warning: OAuth credentials could not be serialized; skipping token cache.")
        
        # Build services
        self.docs_service = build('docs', 'v1', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        self.sheets_service = build('sheets', 'v4', credentials=self.creds)
        
        return True
    
    def create_document(self, title: str, content: str = "") -> dict:
        """Create a new Google Doc"""
        try:
            doc = self.docs_service.documents().create(body={'title': title}).execute()
            doc_id = doc['documentId']
            
            # Add initial content if provided
            if content:
                requests = [{
                    'insertText': {
                        'location': {'index': 1},
                        'text': content
                    }
                }]
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()
            
            return {
                'documentId': doc_id,
                'title': doc['title'],
                'url': f"https://docs.google.com/document/d/{doc_id}/edit",
                'message': 'Document created successfully'
            }
        except HttpError as e:
            raise Exception(f"Failed to create document: {e}")
    
    def read_document(self, document_id: str) -> dict:
        """Read content from a Google Doc"""
        try:
            doc = self.docs_service.documents().get(documentId=document_id).execute()
            
            # Extract text content
            content = doc.get('body', {}).get('content', [])
            text = ""
            
            for element in content:
                if 'paragraph' in element:
                    for text_element in element['paragraph'].get('elements', []):
                        if 'textRun' in text_element:
                            text += text_element['textRun'].get('content', '')
            
            return {
                'documentId': doc['documentId'],
                'title': doc['title'],
                'content': text.strip(),
                'revisionId': doc['revisionId']
            }
        except HttpError as e:
            raise Exception(f"Failed to read document: {e}")
    
    def update_document(self, document_id: str, content: str, mode: str = 'append') -> dict:
        """Update a Google Doc (append or replace)"""
        try:
            requests = []
            
            if mode == 'replace':
                # Get document to find end index
                doc = self.docs_service.documents().get(documentId=document_id).execute()
                body_content = doc.get('body', {}).get('content', [])
                
                if body_content:
                    end_index = body_content[-1].get('endIndex', 1)
                    
                    # Delete all content except first character
                    if end_index > 1:
                        requests.append({
                            'deleteContentRange': {
                                'range': {
                                    'startIndex': 1,
                                    'endIndex': end_index - 1
                                }
                            }
                        })
            
            # Insert new content
            requests.append({
                'insertText': {
                    'location': {'index': 1},
                    'text': content
                }
            })
            
            self.docs_service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}
            ).execute()
            
            return {
                'documentId': document_id,
                'message': f"Document {'replaced' if mode == 'replace' else 'updated'} successfully",
                'url': f"https://docs.google.com/document/d/{document_id}/edit"
            }
        except HttpError as e:
            raise Exception(f"Failed to update document: {e}")
    
    def search_documents(self, query: str, max_results: int = 10) -> dict:
        """Search for Google Docs by name"""
        try:
            response = self.drive_service.files().list(
                q=f"name contains '{query}' and mimeType='application/vnd.google-apps.document'",
                pageSize=max_results,
                fields="files(id, name, createdTime, modifiedTime, webViewLink)"
            ).execute()
            
            files = response.get('files', [])
            
            return {
                'count': len(files),
                'documents': [
                    {
                        'id': f['id'],
                        'name': f['name'],
                        'createdTime': f.get('createdTime'),
                        'modifiedTime': f.get('modifiedTime'),
                        'url': f.get('webViewLink')
                    }
                    for f in files
                ]
            }
        except HttpError as e:
            raise Exception(f"Failed to search documents: {e}")
    
    def list_recent_documents(self, max_results: int = 20) -> dict:
        """List recently modified Google Docs"""
        try:
            response = self.drive_service.files().list(
                q="mimeType='application/vnd.google-apps.document'",
                orderBy='modifiedTime desc',
                pageSize=max_results,
                fields="files(id, name, createdTime, modifiedTime, webViewLink)"
            ).execute()
            
            files = response.get('files', [])
            
            return {
                'count': len(files),
                'documents': [
                    {
                        'id': f['id'],
                        'name': f['name'],
                        'createdTime': f.get('createdTime'),
                        'modifiedTime': f.get('modifiedTime'),
                        'url': f.get('webViewLink')
                    }
                    for f in files
                ]
            }
        except HttpError as e:
            raise Exception(f"Failed to list documents: {e}")

    # ==========================
    # Google Sheets functionality
    # ==========================

    def create_sheet(self, title: str, sheet_name: str = "Sheet1", values: Optional[list[list[Any]]] = None) -> dict:
        """Create a new Google Sheet with optional initial values.

        - title: Spreadsheet title
        - sheet_name: Name of the first sheet (defaults to Sheet1)
        - values: 2D list of cell values to write starting at A1
        """
        try:
            spreadsheet_body = {
                'properties': {'title': title}
            }
            spreadsheet = self.sheets_service.spreadsheets().create(body=spreadsheet_body, fields='spreadsheetId,sheets(properties(sheetId,title))').execute()
            spreadsheet_id = spreadsheet['spreadsheetId']

            # Rename the default first sheet if needed
            first_sheet_props = spreadsheet.get('sheets', [{}])[0].get('properties', {})
            first_sheet_id = first_sheet_props.get('sheetId')
            current_title = first_sheet_props.get('title')
            if first_sheet_id is not None and sheet_name and sheet_name != current_title:
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={
                        'requests': [
                            {
                                'updateSheetProperties': {
                                    'properties': {
                                        'sheetId': first_sheet_id,
                                        'title': sheet_name
                                    },
                                    'fields': 'title'
                                }
                            }
                        ]
                    }
                ).execute()

            # Write initial values if provided
            if values:
                self.sheets_service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"{sheet_name}!A1",
                    valueInputOption='USER_ENTERED',
                    body={'values': values}
                ).execute()

            return {
                'spreadsheetId': spreadsheet_id,
                'title': title,
                'sheetName': sheet_name,
                'url': f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
                'message': 'Spreadsheet created successfully'
            }
        except HttpError as e:
            raise Exception(f"Failed to create sheet: {e}")

    def read_sheet(self, spreadsheet_id: str, range_a1: str) -> dict:
        """Read values from a Google Sheet range (A1 notation)."""
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_a1
            ).execute()
            values = result.get('values', [])
            return {
                'spreadsheetId': spreadsheet_id,
                'range': result.get('range', range_a1),
                'majorDimension': result.get('majorDimension', 'ROWS'),
                'values': values
            }
        except HttpError as e:
            raise Exception(f"Failed to read sheet: {e}")

    def update_sheet(self, spreadsheet_id: str, range_a1: str, values: list[list[Any]], mode: str = 'overwrite', input_mode: str = 'USER_ENTERED') -> dict:
        """Update values in a Google Sheet.

        - mode 'overwrite' uses values.update to replace cells in the range
        - mode 'append' uses values.append to add rows after the table
        """
        try:
            if mode == 'append':
                result = self.sheets_service.spreadsheets().values().append(
                    spreadsheetId=spreadsheet_id,
                    range=range_a1,
                    valueInputOption=input_mode,
                    insertDataOption='INSERT_ROWS',
                    body={'values': values}
                ).execute()
                updated = result.get('updates', {}).get('updatedRows')
            else:
                result = self.sheets_service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=range_a1,
                    valueInputOption=input_mode,
                    body={'values': values}
                ).execute()
                updated = result.get('updatedRows')

            return {
                'spreadsheetId': spreadsheet_id,
                'range': range_a1,
                'mode': mode,
                'updatedRows': updated
            }
        except HttpError as e:
            raise Exception(f"Failed to update sheet: {e}")

    def search_sheets(self, query: str, max_results: int = 10) -> dict:
        """Search for Google Sheets by name using Drive API."""
        try:
            response = self.drive_service.files().list(
                q=f"name contains '{query}' and mimeType='application/vnd.google-apps.spreadsheet'",
                pageSize=max_results,
                fields="files(id, name, createdTime, modifiedTime, webViewLink)"
            ).execute()
            files = response.get('files', [])
            return {
                'count': len(files),
                'spreadsheets': [
                    {
                        'id': f['id'],
                        'name': f['name'],
                        'createdTime': f.get('createdTime'),
                        'modifiedTime': f.get('modifiedTime'),
                        'url': f.get('webViewLink')
                    }
                    for f in files
                ]
            }
        except HttpError as e:
            raise Exception(f"Failed to search sheets: {e}")

    def list_recent_sheets(self, max_results: int = 20) -> dict:
        """List recently modified Google Sheets using Drive API."""
        try:
            response = self.drive_service.files().list(
                q="mimeType='application/vnd.google-apps.spreadsheet'",
                orderBy='modifiedTime desc',
                pageSize=max_results,
                fields="files(id, name, createdTime, modifiedTime, webViewLink)"
            ).execute()

            files = response.get('files', [])
            return {
                'count': len(files),
                'spreadsheets': [
                    {
                        'id': f['id'],
                        'name': f['name'],
                        'createdTime': f.get('createdTime'),
                        'modifiedTime': f.get('modifiedTime'),
                        'url': f.get('webViewLink')
                    }
                    for f in files
                ]
            }
        except HttpError as e:
            raise Exception(f"Failed to list sheets: {e}")