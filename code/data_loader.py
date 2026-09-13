import pandas as pd
import os
from code.security import SecurityContext

class SecureDataLoader:
    def __init__(self, dataset_dir: str):
        self.dataset_dir = dataset_dir
        self.data = self._load_csvs()
        
    def _load_csvs(self):
        data = {}
        for filename in os.listdir(self.dataset_dir):
            if filename.endswith('.csv'):
                name = filename.replace('.csv', '')
                df = pd.read_csv(os.path.join(self.dataset_dir, filename))
                # Normalize user_ids to prevent whitespace bypasses
                if 'user_id' in df.columns:
                    df['user_id'] = df['user_id'].astype(str).str.strip()
                data[name] = df.fillna('')
        return data

    def get_user_requests(self, security_context: SecurityContext) -> list:
        """Returns only the request IDs owned by the authenticated user."""
        df = self.data.get('requests')
        if df is None or df.empty:
            return []
        
        user_id = security_context.dataset_user_id
        return df[df['user_id'] == user_id]['request_id'].tolist()

    def get_request_context(self, request_id: str, security_context: SecurityContext):
        """
        Safely retrieves the full context for a specific request, enforcing IDOR protection.
        """
        df_req = self.data['requests']
        req_row = df_req[df_req['request_id'] == request_id.strip()]
        
        if req_row.empty:
            raise PermissionError("Resource not found or access denied.")
            
        req_row = req_row.iloc[0]
        security_context.verify_ownership(req_row['user_id'])
        
        user_id = security_context.dataset_user_id
        
        prof_df = self.data['financial_profiles']
        prof_row = prof_df[prof_df['user_id'] == user_id].iloc[0]
        
        events_df = self.data['financial_events']
        events_df = events_df[events_df['user_id'] == user_id]
        
        opts_df = self.data['request_payment_options']
        opts_df = opts_df[opts_df['request_id'] == request_id]
        
        messages_df = self.data.get('messages', pd.DataFrame())
        if not messages_df.empty:
            messages_df = messages_df[(messages_df['user_id'] == user_id) & (messages_df['request_id'] == request_id)]
            
        images_df = self.data.get('images', pd.DataFrame())
        if not images_df.empty:
            images_df = images_df[(images_df['user_id'] == user_id) & (images_df['request_id'] == request_id)]
            
        return req_row, prof_row, events_df, opts_df, messages_df, images_df
