use soroban_sdk::{
    contract, contracterror, contractimpl, contracttype, Address, Env, String, Symbol,
};

#[contracterror]
#[derive(Copy, Clone, Debug, Eq, PartialEq, PartialOrd, Ord)]
#[repr(u32)]
pub enum SovereigntyError {
    /// Caller is not the registered owner of the data.
    NotOwner = 1,
    /// The requested data CID was not found in the registry.
    DataNotFound = 2,
    /// Caller does not have access permissions.
    AccessDenied = 3,
    /// The granted access has expired.
    AccessExpired = 4,
    /// This CID has already been registered.
    AlreadyRegistered = 5,
}

#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    /// Maps a CID to its Owner's Address
    Owner(String),
    /// Maps a (CID, Grantee Address) to an Expiration Timestamp (u64)
    Access(String, Address),
}

#[contract]
pub struct DataSovereigntyContract;

#[contractimpl]
impl DataSovereigntyContract {
    /// Registers a new data CID and assigns the caller as the owner.
    pub fn register_data(env: Env, owner: Address, cid: String) -> Result<(), SovereigntyError> {
        // Integrates with Stellar's native multi-sig. If `owner` is a multi-sig account,
        // the network inherently requires the necessary threshold of signatures.
        owner.require_auth();

        let owner_key = DataKey::Owner(cid.clone());
        if env.storage().instance().get::<_, ()>(&owner_key).is_some() {
            return Err(SovereigntyError::AlreadyRegistered);
        }

        // Store metadata in Instance storage for quick lookups
        env.storage().instance().set(&owner_key, &owner);

        env.events().publish(
            (Symbol::new(&env, "data"), Symbol::new(&env, "register")),
            (cid, owner),
        );

        Ok(())
    }

    /// Grants time-bound access to a specific dataset. Requires owner signature.
    pub fn grant_access(
        env: Env,
        owner: Address,
        cid: String,
        grantee: Address,
        expiration_ts: u64,
    ) -> Result<(), SovereigntyError> {
        owner.require_auth();

        let owner_key = DataKey::Owner(cid.clone());
        let actual_owner: Address = env
            .storage()
            .instance()
            .get(&owner_key)
            .ok_or(SovereigntyError::DataNotFound)?;

        if actual_owner != owner {
            return Err(SovereigntyError::NotOwner);
        }

        let access_key = DataKey::Access(cid.clone(), grantee.clone());
        env.storage().instance().set(&access_key, &expiration_ts);

        // Emit event for access modification
        env.events().publish(
            (Symbol::new(&env, "access"), Symbol::new(&env, "granted")),
            (cid, grantee, expiration_ts),
        );

        Ok(())
    }

    /// Revokes access from a grantee prematurely.
    pub fn revoke_access(
        env: Env,
        owner: Address,
        cid: String,
        grantee: Address,
    ) -> Result<(), SovereigntyError> {
        owner.require_auth();

        let owner_key = DataKey::Owner(cid.clone());
        let actual_owner: Address = env
            .storage()
            .instance()
            .get(&owner_key)
            .ok_or(SovereigntyError::DataNotFound)?;

        if actual_owner != owner {
            return Err(SovereigntyError::NotOwner);
        }

        let access_key = DataKey::Access(cid.clone(), grantee.clone());
        env.storage().instance().remove(&access_key);

        env.events().publish(
            (Symbol::new(&env, "access"), Symbol::new(&env, "revoked")),
            (cid, grantee),
        );

        Ok(())
    }

    /// Checks if a caller has valid, unexpired access to query the underlying data.
    ///
    /// NOTE: This is a read-only view function. It deliberately does **not**
    /// invoke `caller.require_auth()` so that other contracts can compose on
    /// top of this access-control layer (e.g. an aggregator contract calling
    /// `check_access` on behalf of its end users). Authorization is enforced
    /// at the point of mutation (`register_data`, `grant_access`,
    /// `revoke_access`) and on the consuming contract, not here.
    /// See GitHub issue #294.
    pub fn check_access(env: Env, cid: String, caller: Address) -> Result<bool, SovereigntyError> {
        // No `caller.require_auth()` here — see issue #294 for rationale.
        let owner_key = DataKey::Owner(cid.clone());
        let actual_owner: Address = env
            .storage()
            .instance()
            .get(&owner_key)
            .ok_or(SovereigntyError::DataNotFound)?;

        // Owner always has access
        if caller == actual_owner {
            return Ok(true);
        }

        // Check grantee access
        let access_key = DataKey::Access(cid, caller);
        if let Some(expiration_ts) = env.storage().instance().get::<_, u64>(&access_key) {
            let current_ts = env.ledger().timestamp();

            if current_ts <= expiration_ts {
                return Ok(true);
            } else {
                return Err(SovereigntyError::AccessExpired);
            }
        }

        Err(SovereigntyError::AccessDenied)
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use soroban_sdk::testutils::{Address as _, Ledger as _};

    #[test]
    fn test_data_registration_and_access() {
        let env = Env::default();
        env.mock_all_auths();

        let contract_id = env.register(DataSovereigntyContract, ());
        let client = DataSovereigntyContractClient::new(&env, &contract_id);

        let owner = Address::generate(&env);
        let cid = String::from_str(&env, "QmHash123...");

        client.register_data(&owner, &cid);
    }

    /// Verifies that `check_access` is composable: a caller can query on
    /// behalf of any other address without that address having to provide a
    /// signature. This is the regression test for issue #294.
    #[test]
    fn test_check_access_is_composable_cross_contract() {
        let env = Env::default();
        env.mock_all_auths();

        let contract_id = env.register(DataSovereigntyContract, ());
        let client = DataSovereigntyContractClient::new(&env, &contract_id);

        let owner = Address::generate(&env);
        let grantee = Address::generate(&env);
        let actor = Address::generate(&env); // a separate contract / relayer
        let cid = String::from_str(&env, "QmComposableHash");
        let expiration_ts = env.ledger().timestamp() + 10_000;

        client.register_data(&owner, &cid);
        client.grant_access(&owner, &cid, &grantee, &expiration_ts);

        // The owner can be queried through `check_access` by anyone,
        // including a third party that did not authorize.
        let owner_ok = client.try_check_access(&cid, &owner);
        assert_eq!(owner_ok, Ok(Ok(true)));

        // A granted grantee is reachable by an unrelated caller (composability).
        let grantee_ok = client.try_check_access(&cid, &grantee);
        assert_eq!(grantee_ok, Ok(Ok(true)));

        // An arbitrary caller that was never granted access is denied.
        let actor_result = client.try_check_access(&cid, &actor);
        assert_eq!(actor_result, Err(Ok(SovereigntyError::AccessDenied)));
    }

    /// A non-existent CID must surface `DataNotFound`, not silently grant access.
    #[test]
    fn test_check_access_unknown_cid_returns_not_found() {
        let env = Env::default();
        env.mock_all_auths();

        let contract_id = env.register(DataSovereigntyContract, ());
        let client = DataSovereigntyContractClient::new(&env, &contract_id);

        let caller = Address::generate(&env);
        let cid = String::from_str(&env, "QmUnknown");

        let result = client.try_check_access(&cid, &caller);
        assert_eq!(result, Err(Ok(SovereigntyError::DataNotFound)));
    }

    /// `check_access` must surface `AccessExpired` (not silently `true`)
    /// once a grantee's window has elapsed.
    #[test]
    fn test_check_access_expired_grant_reports_access_expired() {
        let env = Env::default();
        env.mock_all_auths();

        let contract_id = env.register(DataSovereigntyContract, ());
        let client = DataSovereigntyContractClient::new(&env, &contract_id);

        let owner = Address::generate(&env);
        let grantee = Address::generate(&env);
        let cid = String::from_str(&env, "QmExpired");

        let expiration_ts = env.ledger().timestamp() + 100;
        client.register_data(&owner, &cid);
        client.grant_access(&owner, &cid, &grantee, &expiration_ts);

        // Still valid.
        let before = client.try_check_access(&cid, &grantee);
        assert_eq!(before, Ok(Ok(true)));

        // Cross the expiration boundary.
        env.ledger().set_timestamp(expiration_ts + 1);
        let res = client.try_check_access(&cid, &grantee);
        assert_eq!(res, Err(Ok(SovereigntyError::AccessExpired)));
    }

    /// `revoke_access` must cause `check_access` to surface `AccessDenied`
    /// (the key is gone, so it's not "expired"; the grant was undone).
    #[test]
    fn test_revoked_grantee_is_denied() {
        let env = Env::default();
        env.mock_all_auths();

        let contract_id = env.register(DataSovereigntyContract, ());
        let client = DataSovereigntyContractClient::new(&env, &contract_id);

        let owner = Address::generate(&env);
        let grantee = Address::generate(&env);
        let cid = String::from_str(&env, "QmRevoked");

        client.register_data(&owner, &cid);
        client.grant_access(&owner, &cid, &grantee, &1_000_000);
        client.revoke_access(&owner, &cid, &grantee);

        let res = client.try_check_access(&cid, &grantee);
        assert_eq!(res, Err(Ok(SovereigntyError::AccessDenied)));
    }

    /// A non-owner must not be able to grant/revoke access on a CID they do
    /// not own; the contract surfaces `NotOwner`.
    #[test]
    fn test_non_owner_cannot_grant_or_revoke_access() {
        let env = Env::default();
        env.mock_all_auths();

        let contract_id = env.register(DataSovereigntyContract, ());
        let client = DataSovereigntyContractClient::new(&env, &contract_id);

        let owner = Address::generate(&env);
        let attacker = Address::generate(&env);
        let victim = Address::generate(&env);
        let cid = String::from_str(&env, "QmProtected");

        client.register_data(&owner, &cid);

        let grant = client.try_grant_access(&attacker, &cid, &victim, &1_000_000);
        assert_eq!(grant, Err(Ok(SovereigntyError::NotOwner)));

        // Owner grants legitimate access so we can verify revoke is also
        // gated.
        client.grant_access(&owner, &cid, &victim, &1_000_000);
        let revoke = client.try_revoke_access(&attacker, &cid, &victim);
        assert_eq!(revoke, Err(Ok(SovereigntyError::NotOwner)));
    }
}
