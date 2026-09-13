class SecurityContext:
    def __init__(self, account_uuid: str, dataset_user_id: str):
        self.account_uuid = account_uuid
        self.dataset_user_id = dataset_user_id

    def verify_ownership(self, resource_user_id: str):
        """
        Enforce Resource Ownership.
        Fails closed if the resource does not strictly belong to the authenticated identity.
        """
        if not resource_user_id or not isinstance(resource_user_id, str):
            raise PermissionError("Invalid resource identity.")
            
        if self.dataset_user_id != resource_user_id.strip():
            raise PermissionError("Access Denied: Resource ownership violation.")
