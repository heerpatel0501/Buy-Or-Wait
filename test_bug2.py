import sys, os
root_dir = os.path.dirname(os.path.abspath('main.py'))
sys.path.insert(0, root_dir)
from code.security import SecurityContext
from code.data_loader import SecureDataLoader
from code.app import run_deterministic_engine

dl = SecureDataLoader(os.path.join(root_dir, 'dataset'))
sc = SecurityContext('test', 'user_101')
req_row, prof_row, events_df, opts_df, messages_df, images_df = dl.get_request_context('request_101', sc)

try:
    decision, is_verified = run_deterministic_engine(req_row, prof_row, events_df, opts_df, messages_df, images_df)
    
    # Test metric UI strings
    req_row_curr = prof_row['home_currency']
    prof_curr_avail = prof_row['current_available_balance']
    req_amt = req_row['requested_amount']
    min_bal = prof_row['minimum_balance_to_keep']
    print(f"req_row_curr: {req_row_curr}")
    print(f"prof_curr_avail: {prof_curr_avail}")
    print(f"req_amt: {req_amt}")
    print(f"min_bal: {min_bal}")
    print('Success')
except Exception as e:
    import traceback
    traceback.print_exc()
