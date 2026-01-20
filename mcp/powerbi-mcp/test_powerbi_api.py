#!/usr/bin/env python3
"""
Power BI REST API Test Script
Tests authentication and basic API operations using Service Principal

Usage:
    python test_powerbi_api.py                    # Use Service Principal
    python test_powerbi_api.py --token YOUR_TOKEN # Use specific token
"""

import argparse
import json
import requests
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from auth_helper import get_access_token_service_principal

load_dotenv()

BASE_URL = 'https://api.powerbi.com/v1.0/myorg'


def get_headers(token: str) -> dict:
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }


def test_list_workspaces(token: str) -> list:
    """List all accessible workspaces"""
    print('\n' + '='*60)
    print('📁 LIST WORKSPACES')
    print('='*60)
    
    response = requests.get(f'{BASE_URL}/groups', headers=get_headers(token))
    print(f'Endpoint: GET /groups')
    print(f'Status: {response.status_code}')
    
    if response.status_code == 200:
        workspaces = response.json().get('value', [])
        if workspaces:
            print(f'\n✅ Found {len(workspaces)} workspace(s):\n')
            for ws in workspaces:
                print(f'  📂 {ws["name"]}')
                print(f'     ID: {ws["id"]}')
                print(f'     Type: {ws.get("type", "Workspace")}')
                print(f'     State: {ws.get("state", "Active")}')
                print()
            return workspaces
        else:
            print('\n⚠️  No workspaces found!')
            print('   Service Principal needs to be added to a workspace.')
            print(f'   App ID: {os.getenv("CLIENT_ID", "Not configured")}')
            return []
    else:
        print(f'\n❌ Error: {response.text}')
        return []


def test_list_datasets(token: str, workspace_id: str, workspace_name: str) -> list:
    """List datasets in a workspace"""
    print('\n' + '='*60)
    print(f'📊 LIST DATASETS IN "{workspace_name}"')
    print('='*60)
    
    response = requests.get(
        f'{BASE_URL}/groups/{workspace_id}/datasets', 
        headers=get_headers(token)
    )
    print(f'Endpoint: GET /groups/{workspace_id}/datasets')
    print(f'Status: {response.status_code}')
    
    if response.status_code == 200:
        datasets = response.json().get('value', [])
        if datasets:
            print(f'\n✅ Found {len(datasets)} dataset(s):\n')
            for ds in datasets:
                print(f'  📈 {ds["name"]}')
                print(f'     ID: {ds["id"]}')
                print(f'     Configured By: {ds.get("configuredBy", "N/A")}')
                print(f'     Web URL: {ds.get("webUrl", "N/A")}')
                print()
            return datasets
        else:
            print('\n⚠️  No datasets found in this workspace')
            return []
    else:
        print(f'\n❌ Error: {response.text}')
        return []


def test_list_reports(token: str, workspace_id: str, workspace_name: str) -> list:
    """List reports in a workspace"""
    print('\n' + '='*60)
    print(f'📄 LIST REPORTS IN "{workspace_name}"')
    print('='*60)
    
    response = requests.get(
        f'{BASE_URL}/groups/{workspace_id}/reports', 
        headers=get_headers(token)
    )
    print(f'Endpoint: GET /groups/{workspace_id}/reports')
    print(f'Status: {response.status_code}')
    
    if response.status_code == 200:
        reports = response.json().get('value', [])
        if reports:
            print(f'\n✅ Found {len(reports)} report(s):\n')
            for rpt in reports:
                print(f'  📄 {rpt["name"]}')
                print(f'     ID: {rpt["id"]}')
                print(f'     Dataset ID: {rpt.get("datasetId", "N/A")}')
                print()
            return reports
        else:
            print('\n⚠️  No reports found in this workspace')
            return []
    else:
        print(f'\n❌ Error: {response.text}')
        return []


def test_execute_dax(token: str, workspace_id: str, dataset_id: str, dataset_name: str):
    """Execute a simple DAX query"""
    print('\n' + '='*60)
    print(f'🔍 EXECUTE DAX ON "{dataset_name}"')
    print('='*60)
    
    # Simple DAX query to get table info
    dax_query = "EVALUATE INFO.TABLES()"
    
    payload = {
        "queries": [{"query": dax_query}],
        "serializerSettings": {"includeNulls": True}
    }
    
    response = requests.post(
        f'{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/executeQueries',
        headers=get_headers(token),
        json=payload
    )
    
    print(f'Endpoint: POST /groups/{workspace_id}/datasets/{dataset_id}/executeQueries')
    print(f'Query: {dax_query}')
    print(f'Status: {response.status_code}')
    
    if response.status_code == 200:
        result = response.json()
        tables = result.get('results', [{}])[0].get('tables', [{}])[0].get('rows', [])
        if tables:
            print(f'\n✅ Query returned {len(tables)} table(s):\n')
            for table in tables[:10]:  # Show first 10
                name = table.get('[Name]', 'Unknown')
                print(f'  📋 {name}')
        else:
            print('\n⚠️  No results returned')
    else:
        print(f'\n❌ Error: {response.text}')


def test_get_dataset_tables(token: str, workspace_id: str, dataset_id: str, dataset_name: str):
    """Get tables using COLUMNSTATISTICS DAX"""
    print('\n' + '='*60)
    print(f'📋 GET TABLES FOR "{dataset_name}"')
    print('='*60)
    
    dax_query = "EVALUATE COLUMNSTATISTICS()"
    
    payload = {
        "queries": [{"query": dax_query}],
        "serializerSettings": {"includeNulls": True}
    }
    
    response = requests.post(
        f'{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/executeQueries',
        headers=get_headers(token),
        json=payload
    )
    
    print(f'Endpoint: POST executeQueries')
    print(f'Query: {dax_query}')
    print(f'Status: {response.status_code}')
    
    if response.status_code == 200:
        result = response.json()
        rows = result.get('results', [{}])[0].get('tables', [{}])[0].get('rows', [])
        
        # Group by table name
        tables = {}
        for row in rows:
            table_name = row.get('[Table Name]', 'Unknown')
            col_name = row.get('[Column Name]', 'Unknown')
            if table_name not in tables:
                tables[table_name] = []
            tables[table_name].append(col_name)
        
        if tables:
            print(f'\n✅ Found {len(tables)} table(s):\n')
            for table_name, columns in tables.items():
                print(f'  📋 {table_name} ({len(columns)} columns)')
                for col in columns[:5]:  # Show first 5 columns
                    print(f'      └─ {col}')
                if len(columns) > 5:
                    print(f'      └─ ... and {len(columns) - 5} more')
                print()
        else:
            print('\n⚠️  No tables found')
    else:
        print(f'\n❌ Error: {response.text}')


def main():
    parser = argparse.ArgumentParser(description='Test Power BI REST API')
    parser.add_argument('--token', help='Access token (optional, uses Service Principal if not provided)')
    parser.add_argument('--workspace', help='Specific workspace ID to test')
    parser.add_argument('--dataset', help='Specific dataset ID to test')
    args = parser.parse_args()
    
    print('='*60)
    print('🔌 POWER BI REST API TEST')
    print('='*60)
    
    # Get token
    if args.token:
        token = args.token
        print('Using provided access token')
    else:
        print('Authenticating with Service Principal...')
        token = get_access_token_service_principal()
        if not token:
            print('❌ Failed to acquire token!')
            print('Check CLIENT_ID, TENANT_ID, CLIENT_SECRET in .env')
            return 1
        print('✅ Service Principal authentication successful!')
    
    print(f'Token length: {len(token)} chars')
    
    # Test 1: List Workspaces
    workspaces = test_list_workspaces(token)
    
    if not workspaces:
        print('\n' + '='*60)
        print('🛠️  SETUP REQUIRED')
        print('='*60)
        print('''
To grant the Service Principal access to workspaces:

1. Go to https://app.powerbi.com
2. Create or open a workspace (NOT "My workspace")
3. Click Settings (gear icon) → Manage access
4. Click "Add" and enter the App ID:
   
   5ad188f7-c34d-4b26-8bbf-da87e3926751
   
5. Set permission to "Admin" or "Contributor"
6. Click "Add"
7. Re-run this test
        ''')
        return 0
    
    # Use first workspace or specified one
    if args.workspace:
        ws = next((w for w in workspaces if w['id'] == args.workspace), workspaces[0])
    else:
        ws = workspaces[0]
    
    ws_id = ws['id']
    ws_name = ws['name']
    
    # Test 2: List Datasets
    datasets = test_list_datasets(token, ws_id, ws_name)
    
    # Test 3: List Reports
    test_list_reports(token, ws_id, ws_name)
    
    # Test 4: Execute DAX (if datasets exist)
    if datasets:
        if args.dataset:
            ds = next((d for d in datasets if d['id'] == args.dataset), datasets[0])
        else:
            ds = datasets[0]
        
        ds_id = ds['id']
        ds_name = ds['name']
        
        test_execute_dax(token, ws_id, ds_id, ds_name)
        test_get_dataset_tables(token, ws_id, ds_id, ds_name)
    
    print('\n' + '='*60)
    print('✅ ALL TESTS COMPLETE')
    print('='*60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
