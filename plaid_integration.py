"""
Plaid Integration Module
Handles banking data import, account sync, and transaction fetching
"""
import os
from datetime import datetime, timedelta
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from dotenv import load_dotenv

load_dotenv()

# Plaid Configuration
PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
PLAID_SECRET = os.getenv('PLAID_SECRET')
PLAID_ENV = os.getenv('PLAID_ENV', 'sandbox')  # sandbox, development, or production

# Debug: Print to verify loading
if not PLAID_CLIENT_ID or PLAID_CLIENT_ID == 'your-plaid-client-id-here':
    print("⚠️  WARNING: PLAID_CLIENT_ID not configured in .env file!")
if not PLAID_SECRET or PLAID_SECRET == 'your-plaid-secret-here':
    print("⚠️  WARNING: PLAID_SECRET not configured in .env file!")

# Map environment string to Plaid host
PLAID_HOST_MAP = {
    'sandbox': plaid.Environment.Sandbox,
    'development': plaid.Environment.Sandbox,  # v24+ uses same host
    'production': plaid.Environment.Production
}

# Initialize Plaid client
configuration = plaid.Configuration(
    host=PLAID_HOST_MAP.get(PLAID_ENV, plaid.Environment.Sandbox),
    api_key={
        'clientId': PLAID_CLIENT_ID,
        'secret': PLAID_SECRET,
    }
)

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)


def create_link_token(user_id, username, redirect_uri=None):
    """
    Create a Link token for Plaid Link UI initialization
    
    Args:
        user_id: Internal user ID
        username: Username for display
        redirect_uri: Optional OAuth redirect URI (not needed for basic Link)
        
    Returns:
        link_token: Token for initializing Plaid Link
    """
    try:
        request_params = {
            'products': [Products("auth"), Products("transactions")],
            'client_name': "Credit Repair Pro",
            'country_codes': [CountryCode('US')],
            'language': 'en',
            'user': LinkTokenCreateRequestUser(
                client_user_id=str(user_id)
            )
        }
        
        # Only add redirect_uri if provided
        if redirect_uri:
            request_params['redirect_uri'] = redirect_uri
        
        request = LinkTokenCreateRequest(**request_params)
        
        response = client.link_token_create(request)
        return response['link_token']
        
    except plaid.ApiException as e:
        print(f"Error creating link token: {e}")
        raise


def exchange_public_token(public_token):
    """
    Exchange public token from Plaid Link for access token
    
    Args:
        public_token: Public token from Plaid Link success callback
        
    Returns:
        dict: {access_token, item_id}
    """
    try:
        request = ItemPublicTokenExchangeRequest(
            public_token=public_token
        )
        response = client.item_public_token_exchange(request)
        
        return {
            'access_token': response['access_token'],
            'item_id': response['item_id']
        }
        
    except plaid.ApiException as e:
        print(f"Error exchanging public token: {e}")
        raise


def get_accounts(access_token):
    """
    Fetch all accounts for a Plaid item
    
    Args:
        access_token: Plaid access token
        
    Returns:
        list: Account objects with balances and details
    """
    try:
        request = AccountsBalanceGetRequest(
            access_token=access_token
        )
        response = client.accounts_balance_get(request)
        
        accounts = []
        for account in response['accounts']:
            accounts.append({
                'plaid_account_id': account['account_id'],
                'name': account['name'],
                'official_name': account.get('official_name'),
                'type': account['type'],
                'subtype': account['subtype'],
                'mask': account['mask'],
                'current_balance': account['balances'].get('current'),
                'available_balance': account['balances'].get('available'),
                'limit': account['balances'].get('limit'),
                'currency': account['balances']['iso_currency_code']
            })
        
        return {
            'accounts': accounts,
            'institution': response.get('item', {})
        }
        
    except plaid.ApiException as e:
        print(f"Error fetching accounts: {e}")
        raise


def sync_transactions(access_token, cursor=None, count=500):
    """
    Sync transactions using Plaid Transactions Sync API
    Pulls all new/modified transactions since last sync
    
    Args:
        access_token: Plaid access token
        cursor: Cursor for pagination (None for initial sync)
        count: Number of transactions to fetch per request
        
    Returns:
        dict: {transactions, cursor, has_more}
    """
    try:
        request = TransactionsSyncRequest(
            access_token=access_token,
            cursor=cursor,
            count=count
        )
        response = client.transactions_sync(request)
        
        transactions = []
        for txn in response['added']:
            transactions.append({
                'plaid_transaction_id': txn['transaction_id'],
                'plaid_account_id': txn['account_id'],
                'amount': float(txn['amount']),
                'date': txn['date'].isoformat() if hasattr(txn['date'], 'isoformat') else str(txn['date']),
                'name': txn['name'],
                'merchant_name': txn.get('merchant_name'),
                'category': txn.get('category', []),
                'payment_channel': txn['payment_channel'],
                'pending': txn['pending'],
                'transaction_type': txn.get('transaction_type'),
                'authorized_date': txn.get('authorized_date').isoformat() if txn.get('authorized_date') else None,
            })
        
        return {
            'transactions': transactions,
            'cursor': response['next_cursor'],
            'has_more': response['has_more']
        }
        
    except plaid.ApiException as e:
        print(f"Error syncing transactions: {e}")
        raise


def search_payment_transactions(access_token, creditor_name, min_amount=None, max_amount=None, 
                                start_date=None, end_date=None):
    """
    Search transactions for payments to a specific creditor
    Useful for generating payment proof for disputes
    
    Args:
        access_token: Plaid access token
        creditor_name: Name to search for (e.g., "Capital One", "Chase")
        min_amount: Minimum transaction amount (optional)
        max_amount: Maximum transaction amount (optional)
        start_date: Start date for search (datetime, optional)
        end_date: End date for search (datetime, optional)
        
    Returns:
        list: Matching transactions
    """
    try:
        # Fetch all transactions (paginated if needed)
        all_transactions = []
        cursor = None
        has_more = True
        
        while has_more:
            sync_result = sync_transactions(access_token, cursor=cursor)
            all_transactions.extend(sync_result['transactions'])
            cursor = sync_result['cursor']
            has_more = sync_result['has_more']
        
        # Filter transactions
        matching_transactions = []
        creditor_lower = creditor_name.lower()
        
        for txn in all_transactions:
            # Check name match
            name_match = (creditor_lower in txn['name'].lower() or 
                         (txn.get('merchant_name') and creditor_lower in txn['merchant_name'].lower()))
            
            if not name_match:
                continue
            
            # Check amount range
            if min_amount and txn['amount'] < min_amount:
                continue
            if max_amount and txn['amount'] > max_amount:
                continue
            
            # Check date range
            txn_date = datetime.fromisoformat(txn['date']) if isinstance(txn['date'], str) else txn['date']
            if start_date and txn_date < start_date:
                continue
            if end_date and txn_date > end_date:
                continue
            
            matching_transactions.append(txn)
        
        return matching_transactions
        
    except Exception as e:
        print(f"Error searching transactions: {e}")
        raise


def detect_collections_accounts(access_token):
    """
    Detect potential collections accounts from linked accounts
    Looks for accounts with negative impacts (charge-offs, collections)
    
    Args:
        access_token: Plaid access token
        
    Returns:
        list: Accounts that may need dispute
    """
    try:
        accounts_data = get_accounts(access_token)
        potential_disputes = []
        
        for account in accounts_data['accounts']:
            # Look for loan/credit accounts with negative status
            if account['type'] in ['credit', 'loan', 'other']:
                # Check for negative balance on credit accounts (shouldn't happen)
                # Check for closed accounts with balances
                # This is basic heuristic - real implementation would need credit report data
                
                if account['type'] == 'credit' and account.get('current_balance', 0) > 0:
                    # Credit card with balance - potential for disputes if paid off
                    potential_disputes.append({
                        'account': account,
                        'reason': 'Credit account with balance - verify if paid or disputed',
                        'suggested_action': 'Check if this matches any credit report entries'
                    })
        
        return potential_disputes
        
    except Exception as e:
        print(f"Error detecting collections: {e}")
        raise


def generate_payment_proof_data(transactions, creditor_name):
    """
    Generate structured data for payment proof document
    
    Args:
        transactions: List of matching transactions
        creditor_name: Name of creditor
        
    Returns:
        dict: Formatted data for PDF generation
    """
    total_paid = sum(txn['amount'] for txn in transactions)
    
    return {
        'creditor_name': creditor_name,
        'total_paid': total_paid,
        'payment_count': len(transactions),
        'first_payment_date': min(txn['date'] for txn in transactions) if transactions else None,
        'last_payment_date': max(txn['date'] for txn in transactions) if transactions else None,
        'transactions': sorted(transactions, key=lambda x: x['date'], reverse=True),
        'generated_at': datetime.now().isoformat()
    }


def get_account_verification_data(access_token, account_mask):
    """
    Get verification data for proving account ownership
    Useful for identity verification in disputes
    
    Args:
        access_token: Plaid access token
        account_mask: Last 4 digits of account number
        
    Returns:
        dict: Account verification data
    """
    try:
        accounts_data = get_accounts(access_token)
        
        for account in accounts_data['accounts']:
            if account['mask'] == account_mask:
                return {
                    'account_name': account['name'],
                    'official_name': account['official_name'],
                    'type': account['type'],
                    'subtype': account['subtype'],
                    'mask': account['mask'],
                    'current_balance': account['current_balance'],
                    'verified': True,
                    'verification_date': datetime.now().isoformat()
                }
        
        return None
        
    except Exception as e:
        print(f"Error getting verification data: {e}")
        raise
