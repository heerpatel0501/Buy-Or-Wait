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
                if 'user_id' in df.columns:
                    df['user_id'] = df['user_id'].astype(str).str.strip()
                data[name] = df.fillna('')
        return data

    def get_user_requests(self, security_context: SecurityContext) -> list:
        df_reqs = self.data.get('requests')
        df_samples = self.data.get('sample_requests')
        
        all_reqs = []
        user_id = security_context.dataset_user_id
        
        if df_reqs is not None and not df_reqs.empty:
            all_reqs.extend(df_reqs[df_reqs['user_id'] == user_id]['request_id'].tolist())
            
        if df_samples is not None and not df_samples.empty:
            all_reqs.extend(df_samples[df_samples['user_id'] == user_id]['request_id'].tolist())
            
        return all_reqs

    def get_request_context(self, request_id: str, security_context: SecurityContext):
        req_id_clean = request_id.strip()
        
        # Search in requests.csv first, then sample_requests.csv
        df_req = self.data.get('requests')
        req_row_df = df_req[df_req['request_id'] == req_id_clean] if df_req is not None else pd.DataFrame()
        
        if req_row_df.empty:
            df_sample = self.data.get('sample_requests')
            req_row_df = df_sample[df_sample['request_id'] == req_id_clean] if df_sample is not None else pd.DataFrame()
            
        if req_row_df.empty:
            raise KeyError(f"Request {req_id_clean} not found in any dataset.")
            
        req_row = req_row_df.iloc[0]
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
            
        rates_df = self.data.get('exchange_rates', pd.DataFrame())
            
        return req_row, prof_row, events_df, opts_df, messages_df, images_df, rates_df
