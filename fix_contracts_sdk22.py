#!/usr/bin/env python3
"""Fix remaining SDK 22 compilation errors across all contracts source files."""

import os
import re

CONTRACTS_SRC = "/workspaces/stellar-privacy-analytics/contracts/src"

def fix_file(filepath, content):
    original = content
    
    # ============================================================
    # 1. Fix .into() calls on soroban values -> .into_val(&env)
    #    Matches: variable.into() where variable is a soroban type
    #    Only in Vec::push_back context where env is available
    # ============================================================
    # Pattern: push_back(xxx.into()) where xxx is a clone of a soroban type
    content = re.sub(
        r'\.push_back\((\w+(?:\.\w+)*)\.into\(\)\)',
        r'.push_back(\1.into_val(&env))',
        content
    )
    
    # ============================================================
    # 2. Fix Map::set with &i128, &u64 references -> owned values
    # ============================================================
    # Map::set(key, &<number>i128) -> Map::set(key, <number>i128)
    content = re.sub(
        r'\.set\(([^,]+),\s*&(\d+i128)\)',
        r'.set(\1, \2)',
        content
    )
    
    # Map::set(key, &0u64) -> Map::set(key, 0u64)
    content = re.sub(
        r'\.set\(([^,]+),\s*&(0u64)\)',
        r'.set(\1, \2)',
        content
    )
    
    # ============================================================
    # 3. Fix .to_array() on String -> use .to_xdr(&env) approach
    #    Replace: string_var.to_array() -> string_var.to_xdr(&env)
    #    But this doesn't return the same type. Better: use 
    #    the string directly in a Vec and to_xdr the whole Vec.
    #    For the sha256 ID generation patterns, replace:
    #    combined.append(&name.to_array()) -> combined.append(&name.to_xdr(env))
    # ============================================================
    # In schema_enforcer.rs generate functions:
    # name.to_array() -> name.to_xdr(env)
    content = re.sub(
        r'(\w+)\.to_array\(\)',
        r'\1.to_xdr(env)',
        content
    )
    
    # Fix the double && from above when already has &
    content = content.replace('&&', '&')
    
    # ============================================================
    # 4. Fix env.crypto().sha256() returning Hash<32> used as BytesN<32>
    #    In struct fields and Map keys, convert:
    #    let key_id = env.crypto().sha256(&data);
    #    AccessKey { key_id, ... }
    #    ->
    #    let key_id_hash = env.crypto().sha256(&data);
    #    let key_id = BytesN::from_array(&env, &key_id_hash.to_array());
    # ============================================================
    
    # Fix: let request_id = env.crypto().sha256(&input_data.to_xdr(env));
    # Need to wrap in BytesN::from_array
    content = re.sub(
        r'let (\w+) = env\.crypto\(\)\.sha256\(&(\w+)\.to_xdr\(env\)\);',
        r'let \1_hash = env.crypto().sha256(&\2.to_xdr(env));\n        let \1 = BytesN::from_array(&env, &\1_hash.to_array());',
        content
    )
    
    # Fix: let request_id = env.crypto().sha256(&input_data.to_xdr(&env));
    content = re.sub(
        r'let (\w+) = env\.crypto\(\)\.sha256\(&(\w+)\.to_xdr\(&env\)\);',
        r'let \1_hash = env.crypto().sha256(&\2.to_xdr(&env));\n        let \1 = BytesN::from_array(&env, &\1_hash.to_array());',
        content
    )
    
    # Fix: let key_id = env.crypto().sha256(&key_data);
    # where key_data is already Bytes from to_xdr
    content = re.sub(
        r'let (\w+) = env\.crypto\(\)\.sha256\(&(\w+)\);\s*\n\s*// Create access key',
        r'let \1_hash = env.crypto().sha256(&\2);\n        let \1 = BytesN::from_array(&env, &\1_hash.to_array());\n\n        // Create access key',
        content
    )
    
    # Fix: result_hash = env.crypto().sha256(&encrypted_result);
    # In struct literal initializer
    content = re.sub(
        r'let (\w+) = env\.crypto\(\)\.sha256\(&(\w+)\);',
        r'let \1_hash = env.crypto().sha256(&\2);\n        let \1 = BytesN::from_array(&env, &\1_hash.to_array());',
        content
    )
    
    # Fix: data_hash: env.crypto().sha256(&data),
    content = re.sub(
        r'data_hash: env\.crypto\(\)\.sha256\(&(\w+)\)',
        r'data_hash: BytesN::from_array(env, &env.crypto().sha256(&\1).to_array())',
        content
    )
    
    # ============================================================
    # 5. Fix Symbol::new(...).concat(...) -> tuple keys
    # ============================================================
    # Symbol::new(&env, "result_").concat(&request_id)
    # -> (Symbol::new(&env, "result_"), request_id.clone())
    content = re.sub(
        r'Symbol::new\(&env, "([^"]+)"\)\.concat\(&(\w+)\)',
        r'(Symbol::new(&env, "\1"), \2.clone())',
        content
    )
    
    # ============================================================
    # 6. Fix Vec::slice(start..end) -> manual approach  
    #    In access_control.rs log_access
    # ============================================================
    # access_log = access_log.slice(start_idx..end_idx);
    # ->
    # let mut new_log = Vec::new(env); 
    # for i in start_idx..end_idx { if let Some(entry) = access_log.get(i) { new_log.push_back(entry); } }
    # access_log = new_log;
    old_slice = r'access_log = access_log\.slice\((\w+)\.\.(\w+)\);'
    new_slice = r'''let mut _new_log = Vec::new(env);
        for _i in \1..\2 {
            if let Some(_entry) = access_log.get(_i) {
                _new_log.push_back(_entry);
            }
        }
        access_log = _new_log;'''
    content = re.sub(old_slice, new_slice, content)
    
    # ============================================================
    # 7. Fix move value issues in admin.rs
    #    transaction_hash used after move
    # ============================================================
    # In submit_transaction: executions.set(transaction_hash, transaction);
    # but transaction_hash also used later in events
    # Need to clone before set
    content = re.sub(
        r'executions\.set\((\w+), (\w+)\);',
        r'executions.set(\1.clone(), \2);',
        content
    )
    
    # Fix: confirmations.set(transaction_hash, tx_confirmations);
    content = re.sub(
        r'confirmations\.set\((\w+), (\w+)\);',
        r'confirmations.set(\1.clone(), \2);',
        content
    )
    
    # Fix: permissions.set(user, &updated_permissions);
    content = re.sub(
        r'permissions\.set\((\w+), &(\w+)\);',
        r'permissions.set(\1.clone(), \2);',
        content
    )
    
    # Fix: requests.set(request_id.clone(), request.clone());
    # Already uses clone, this is fine
    
    # ============================================================
    # 8. Fix storages that store &contracttype -> owned  
    #    Map::set with &access_key, &resource_owner, etc.
    # ============================================================
    # access_keys.set(key_id, &access_key) -> access_keys.set(key_id, access_key)
    content = re.sub(
        r'(\w+)\.set\((\w+),\s*&(\w+)\);',
        r'\1.set(\2, \3);',
        content
    )
    
    # Fix Map set with &updated_permissions where updated_permissions is Vec
    content = re.sub(
        r'(\w+)\.set\((\w+),\s*&(\w+)\)',
        r'\1.set(\2, \3)',
        content
    )
    
    # ============================================================
    # 9. Fix admin.rs hash_transaction returning Hash<32> not BytesN<32>
    # ============================================================
    content = re.sub(
        r'env\.crypto\(\)\.sha256\(&data\.to_xdr\(&env\)\)',
        r'BytesN::from_array(&env, &env.crypto().sha256(&data.to_xdr(&env)).to_array())',
        content
    )
    
    # ============================================================
    # 10. Fix privacy_levels initialization: already uses owned PrivacyLevel
    #     (they were fixed in previous round - verify)
    # ============================================================
    
    # ============================================================
    # 11. Fix .get(i).unwrap_or(&0) on Bytes -> Bytes::get returns Result  
    #     Change: value.get(i).unwrap_or(&0)
    #     -> value.get(i).unwrap_or(0)
    # ============================================================
    content = re.sub(
        r'\.get\((\w+)\)\.unwrap_or\(&(\w+)\)',
        r'.get(\1).unwrap_or(\2)',
        content
    )
    
    # ============================================================
    # 12. Fix privacy_levels Map<String, PrivacyLevel>::get needs String key
    #     Already correct in stellar_analytics.rs
    # ============================================================
    
    if content != original:
        return content
    return None

def main():
    fixed_files = []
    for f in sorted(os.listdir(CONTRACTS_SRC)):
        if not f.endswith('.rs'):
            continue
        filepath = os.path.join(CONTRACTS_SRC, f)
        with open(filepath) as fh:
            content = fh.read()
        
        result = fix_file(filepath, content)
        if result is not None:
            with open(filepath, 'w') as fh:
                fh.write(result)
            fixed_files.append(f)
            print(f"Fixed: {f}")
    
    if not fixed_files:
        print("No files needed fixing")
    else:
        print(f"\nTotal files fixed: {len(fixed_files)}")

if __name__ == "__main__":
    main()
