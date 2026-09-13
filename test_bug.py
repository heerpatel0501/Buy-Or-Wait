import sys, os
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)
from code.security import SecurityContext
from code.data_loader import SecureDataLoader
from code.app import run_deterministic_engine

dl = SecureDataLoader(os.path.join(root_dir, 'dataset'))
sc = SecurityContext("test", "user_101")
req_row, prof_row, events_df, opts_df, messages_df, images_df = dl.get_request_context('request_101', sc)

try:
    run_deterministic_engine(req_row, prof_row, events_df, opts_df, messages_df, images_df)
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
